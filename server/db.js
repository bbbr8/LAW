import { open } from 'sqlite'
import sqlite3 from 'sqlite3'

export async function initDb() {
  const db = await open({ filename: './server/database.sqlite', driver: sqlite3.Database })
  await db.exec(`CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, data TEXT)`)
  await db.exec(`CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, caseId TEXT, data TEXT)`)
  await db.exec(`CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, caseId TEXT, data TEXT)`)
  return db
}
