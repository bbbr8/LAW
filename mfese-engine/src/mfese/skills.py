from __future__ import annotations
import hashlib, io, json, mimetypes, re, time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Sequence
import cv2, fitz, numpy as np
from PIL import Image
from pydantic import BaseModel, Field
from sklearn.preprocessing import normalize
from skimage.feature import hog

ENGINE_VERSION="1.1.0"
BOUNDARY=("Fingerprints, similarities, embeddings and anomaly signals are review aids. They do not independently prove alteration, authorship, identity, authorization, intent, payment application, damages, fraud or liability. Native bytes and authenticated custody records control.")
class EvidenceClass(str,Enum): NATIVE="F0_NATIVE_MEASUREMENT"; CALC="F1_REPRODUCIBLE_CALCULATION"; MODEL="MODEL_CANDIDATE_PROMOTION_BLOCKED"; REVIEW="REVIEW_SIGNAL"; OPEN="OPEN"
class SkillStatus(str,Enum): OK="ok"; SKIPPED="skipped"; ERROR="error"
@dataclass(slots=True)
class SkillResult:
    skill_id:str; status:SkillStatus; evidence_class:EvidenceClass; measurements:dict[str,Any]=field(default_factory=dict); warnings:list[str]=field(default_factory=list); model:dict[str,Any]|None=None; elapsed_ms:int=0
class WizardReport(BaseModel):
    schema_version:str="cvfs-wizard-report/v1"; engine_version:str=ENGINE_VERSION; generated_utc:str; source:dict[str,Any]; boundary:str=BOUNDARY; skills:list[dict[str,Any]]; summary:dict[str,Any]; errors:list[str]=Field(default_factory=list)
MODEL_SPECS={"dinov2":{"repo_id":"facebook/dinov2-base"},"siglip2":{"repo_id":"google/siglip2-base-patch16-224"},"table_detection":{"repo_id":"microsoft/table-transformer-detection"}}
DEFAULT_SKILLS=("source_identity","pdf_structure","page_fingerprints","embedded_objects","text_layer","form_signature_structure","scanner_fingerprint","signature_candidates")
def _sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def _safe(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    if isinstance(v,bytes):return {"sha256":_sha(v),"length":len(v)}
    if isinstance(v,np.ndarray):return v.tolist()
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,dict):return {str(k):_safe(x) for k,x in v.items()}
    if isinstance(v,(list,tuple,set)):return [_safe(x) for x in v]
    return str(v)
def _mime(p:Path)->str:return "application/pdf" if p.suffix.lower()==".pdf" else (mimetypes.guess_type(p.name)[0] or "application/octet-stream")
def _bgr(pix):
    a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n);return cv2.cvtColor(a,cv2.COLOR_RGBA2BGR if pix.n==4 else cv2.COLOR_RGB2BGR)
def _phash(img,size=8):
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY);d=cv2.dct(np.float32(cv2.resize(g,(size*4,size*4),interpolation=cv2.INTER_AREA)))[:size,:size];return np.packbits((d>np.median(d[1:])).astype(np.uint8).reshape(-1)).tobytes().hex()
def _dhash(img,size=8):
    g=cv2.resize(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY),(size+1,size),interpolation=cv2.INTER_AREA);return np.packbits((g[:,1:]>g[:,:-1]).astype(np.uint8).reshape(-1)).tobytes().hex()
def _hog(img):
    g=cv2.resize(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY),(256,320),interpolation=cv2.INTER_AREA);return normalize(hog(g,orientations=9,pixels_per_cell=(16,16),cells_per_block=(2,2),feature_vector=True).reshape(1,-1))[0]
def _scanner(img):
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY);s=min(1,1400/max(g.shape));g=cv2.resize(g,None,fx=s,fy=s,interpolation=cv2.INTER_AREA) if s<1 else g;e=cv2.Canny(g,80,180);h=np.histogram(g,bins=256,range=(0,256),density=True)[0];h=h[h>0];b=np.concatenate([g[0],g[-1],g[:,0],g[:,-1]])
    return {"blur":float(cv2.Laplacian(g,cv2.CV_64F).var()),"edge_density":float(np.mean(e>0)),"entropy":float(-np.sum(h*np.log2(h))),"border_mean":float(np.mean(b)),"border_std":float(np.std(b))}
def _signatures(img,limit=20):
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY);start=int(g.shape[0]*.45);roi=g[start:];bw=cv2.threshold(roi,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1];bw=cv2.morphologyEx(bw,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(5,2)));contours,_=cv2.findContours(bw,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);rows=[]
    for c in contours:
        x,y,w,h=cv2.boundingRect(c);area=cv2.contourArea(c)
        if w>=45 and h>=8 and area>=60 and w/max(h,1)>=1.5:
            crop=roi[y:y+h,x:x+w];rows.append({"bbox":[x,y+start,x+w,y+h+start],"area":float(area),"crop_sha256":_sha(crop.tobytes()),"phash":_phash(cv2.cvtColor(crop,cv2.COLOR_GRAY2BGR))})
    return sorted(rows,key=lambda r:r["area"],reverse=True)[:limit]
class ForensicWizard:
    def __init__(self,*,allow_network_models=False,device=None):self.allow_network_models=allow_network_models;self.device=device or "cpu";self._models={}
    def scan_file(self,path,*,skills=None,enable_models=None,render_dpi=150):
        p=Path(path);data=p.read_bytes();rows=[];errors=[]
        for sid in skills or DEFAULT_SKILLS:
            t=time.perf_counter()
            try:r=getattr(self,f"skill_{sid}")(p,data,render_dpi=render_dpi)
            except Exception as exc:r=SkillResult(sid,SkillStatus.ERROR,EvidenceClass.OPEN,warnings=[str(exc)]);errors.append(f"{sid}: {exc}")
            r.elapsed_ms=int((time.perf_counter()-t)*1000);rows.append(r)
        for mid in enable_models or ():
            t=time.perf_counter()
            try:r=self._run_model(mid,p,render_dpi)
            except Exception as exc:r=SkillResult(f"hf_{mid}",SkillStatus.ERROR,EvidenceClass.MODEL,warnings=[str(exc)],model=MODEL_SPECS.get(mid));errors.append(f"hf_{mid}: {exc}")
            r.elapsed_ms=int((time.perf_counter()-t)*1000);rows.append(r)
        return WizardReport(generated_utc=datetime.now(timezone.utc).isoformat(),source={"name":p.name,"size":len(data),"sha256":_sha(data),"mime_type":_mime(p)},skills=[_safe(asdict(r)) for r in rows],summary={"ok":sum(r.status==SkillStatus.OK for r in rows),"errors":len(errors)},errors=errors)
    def skill_source_identity(self,p,data,**k):return SkillResult("source_identity",SkillStatus.OK,EvidenceClass.NATIVE,{"name":p.name,"size":len(data),"sha256":_sha(data),"mime_type":_mime(p)})
    def skill_pdf_structure(self,p,data,**k):
        if p.suffix.lower()!=".pdf":return SkillResult("pdf_structure",SkillStatus.SKIPPED,EvidenceClass.NATIVE)
        d=fitz.open(stream=data,filetype="pdf");m=re.search(rb"%PDF-(\d\.\d)",data[:1024]);x={"page_count":d.page_count,"pdf_version":m.group(1).decode() if m else None,"startxref_count":len(re.findall(rb"startxref",data)),"eof_count":len(re.findall(rb"%%EOF",data)),"prev_pointer_count":len(re.findall(rb"/Prev\s+\d+",data)),"has_acroform":b"/AcroForm" in data,"has_signature_dictionary":bool(re.search(rb"/Type\s*/Sig|/FT\s*/Sig",data)),"has_javascript":bool(re.search(rb"/(JavaScript|JS)\b",data)),"has_embedded_files":b"/EmbeddedFiles" in data or b"/Filespec" in data,"metadata":{a:b for a,b in (d.metadata or {}).items() if b},"byte_ranges":[v.decode(errors="replace") for v in re.findall(rb"/ByteRange\s*\[([^\]]+)\]",data)]};d.close();return SkillResult("pdf_structure",SkillStatus.OK,EvidenceClass.NATIVE,x,["Multiple saves are a provenance question."] if x["startxref_count"]>1 or x["prev_pointer_count"] else [])
    def skill_page_fingerprints(self,p,data,*,render_dpi=150,**k):
        pages=[]
        if p.suffix.lower()==".pdf":
            d=fitz.open(stream=data,filetype="pdf")
            for i,page in enumerate(d):
                pix=page.get_pixmap(dpi=render_dpi,alpha=False);img=_bgr(pix);v=_hog(img);pages.append({"page":i+1,"raster_sha256":_sha(pix.samples),"phash":_phash(img),"dhash":_dhash(img),"hog_embedding":np.round(v,7).tolist(),"width_pt":float(page.rect.width),"height_pt":float(page.rect.height),"rotation":int(page.rotation)})
            d.close()
        else:
            im=Image.open(io.BytesIO(data)).convert("RGB");img=cv2.cvtColor(np.array(im),cv2.COLOR_RGB2BGR);v=_hog(img);pages=[{"page":1,"raster_sha256":_sha(np.array(im).tobytes()),"phash":_phash(img),"dhash":_dhash(img),"hog_embedding":np.round(v,7).tolist()}]
        return SkillResult("page_fingerprints",SkillStatus.OK,EvidenceClass.CALC,{"render_dpi":render_dpi,"pages":pages})
    def skill_embedded_objects(self,p,data,**k):
        if p.suffix.lower()!=".pdf":return SkillResult("embedded_objects",SkillStatus.SKIPPED,EvidenceClass.NATIVE)
        d=fitz.open(stream=data,filetype="pdf");rows=[]
        for i,page in enumerate(d):
            for r in page.get_images(full=True):
                try:x=d.extract_image(r[0]);payload=x.get("image",b"");rows.append({"page":i+1,"xref":r[0],"width":r[2],"height":r[3],"smask":r[1],"filter":r[8],"embedded_sha256":_sha(payload),"length":len(payload),"extension":x.get("ext")})
                except Exception as exc:rows.append({"page":i+1,"xref":r[0],"error":str(exc)})
        d.close();return SkillResult("embedded_objects",SkillStatus.OK,EvidenceClass.NATIVE,{"objects":rows})
    def skill_text_layer(self,p,data,**k):
        if p.suffix.lower()!=".pdf":return SkillResult("text_layer",SkillStatus.SKIPPED,EvidenceClass.NATIVE)
        d=fitz.open(stream=data,filetype="pdf");rows=[]
        for i,page in enumerate(d):
            spans=[];outside=white=0
            for block in page.get_text("dict").get("blocks",[]):
                for line in block.get("lines",[]):
                    for s in line.get("spans",[]):
                        box=s.get("bbox",[0,0,0,0]);color=int(s.get("color",0));outside+=box[2]<0 or box[3]<0 or box[0]>page.rect.width or box[1]>page.rect.height;white+=color==16777215;spans.append({"text":s.get("text",""),"bbox":box,"font":s.get("font"),"size":s.get("size"),"color":color})
            rows.append({"page":i+1,"span_count":len(spans),"outside_page_count":outside,"white_text_count":white,"spans":spans})
        d.close();return SkillResult("text_layer",SkillStatus.OK,EvidenceClass.NATIVE,{"pages":rows},["White/outside text may be OCR or accessibility content."])
    def skill_form_signature_structure(self,p,data,**k):
        if p.suffix.lower()!=".pdf":return SkillResult("form_signature_structure",SkillStatus.SKIPPED,EvidenceClass.NATIVE)
        d=fitz.open(stream=data,filetype="pdf");widgets=[]
        for i,page in enumerate(d):
            w=page.first_widget
            while w:widgets.append({"page":i+1,"field_name":w.field_name,"field_type":w.field_type_string,"field_value":_safe(w.field_value),"field_flags":int(w.field_flags),"rect":list(w.rect)});w=w.next
        d.close();return SkillResult("form_signature_structure",SkillStatus.OK,EvidenceClass.NATIVE,{"widgets":widgets,"byte_ranges":[v.decode(errors="replace") for v in re.findall(rb"/ByteRange\s*\[([^\]]+)\]",data)],"signature_dictionary_count":len(re.findall(rb"/Type\s*/Sig|/FT\s*/Sig",data)),"pkcs7_markers":len(re.findall(rb"adbe\.pkcs7|ETSI\.CAdES",data,re.I))},["Visible appearance, cryptographic validity and authority are separate."])
    def skill_scanner_fingerprint(self,p,data,*,render_dpi=150,**k):
        if p.suffix.lower()==".pdf":
            d=fitz.open(stream=data,filetype="pdf");rows=[{"page":i+1,**_scanner(_bgr(page.get_pixmap(dpi=render_dpi,alpha=False)))} for i,page in enumerate(d)];d.close()
        else:im=Image.open(io.BytesIO(data)).convert("RGB");rows=[{"page":1,**_scanner(cv2.cvtColor(np.array(im),cv2.COLOR_RGB2BGR))}]
        return SkillResult("scanner_fingerprint",SkillStatus.OK,EvidenceClass.REVIEW,{"features":rows,"fingerprint_sha256":_sha(json.dumps(rows,sort_keys=True).encode())},["Scanner similarity cannot identify an operator."])
    def skill_signature_candidates(self,p,data,*,render_dpi=200,**k):
        if p.suffix.lower()==".pdf":
            d=fitz.open(stream=data,filetype="pdf");rows=[{"page":i+1,"candidates":_signatures(_bgr(page.get_pixmap(dpi=render_dpi,alpha=False)))} for i,page in enumerate(d)];d.close()
        else:im=Image.open(io.BytesIO(data)).convert("RGB");rows=[{"page":1,"candidates":_signatures(cv2.cvtColor(np.array(im),cv2.COLOR_RGB2BGR))}]
        return SkillResult("signature_candidates",SkillStatus.OK,EvidenceClass.REVIEW,{"pages":rows},["Candidates include signatures, initials, rules, logos and handwriting."])
    def _run_model(self,mid,p,dpi):
        if not self.allow_network_models:raise RuntimeError("Network model execution is disabled")
        import torch
        from transformers import AutoImageProcessor,AutoModel,AutoModelForObjectDetection
        repo=MODEL_SPECS[mid]["repo_id"];processor=AutoImageProcessor.from_pretrained(repo);model=AutoModelForObjectDetection.from_pretrained(repo) if mid=="table_detection" else AutoModel.from_pretrained(repo);model.to(self.device).eval();doc=fitz.open(p) if p.suffix.lower()==".pdf" else None;im=Image.frombytes("RGB",(doc[0].get_pixmap(dpi=dpi,alpha=False).width,doc[0].get_pixmap(dpi=dpi,alpha=False).height),doc[0].get_pixmap(dpi=dpi,alpha=False).samples) if doc else Image.open(p).convert("RGB");doc.close() if doc else None;inputs={k:v.to(self.device) for k,v in processor(images=im,return_tensors="pt").items()}
        with torch.inference_mode():out=model(**inputs)
        if mid=="table_detection":
            z=processor.post_process_object_detection(out,threshold=.75,target_sizes=torch.tensor([im.size[::-1]],device=self.device))[0];m={"detections":[{"score":float(s.cpu()),"label_id":int(l.cpu()),"box":[round(float(v),2) for v in b.cpu().tolist()]} for s,l,b in zip(z["scores"],z["labels"],z["boxes"])]}
        else:v=torch.nn.functional.normalize(out.last_hidden_state.mean(dim=1),dim=-1)[0].detach().cpu().float().numpy();m={"embedding_dimensions":int(v.shape[0]),"embedding_sha256":_sha(v.tobytes()),"embedding":np.round(v,7).tolist()}
        return SkillResult(f"hf_{mid}",SkillStatus.OK,EvidenceClass.MODEL,m,["Model output is promotion blocked."],MODEL_SPECS[mid])
