/** Records one chapter of the live series: node record-live.mjs <1-12>.  FAST=1 runs the steps without voice or video (rehearsal). */
import { assertNoSecret } from '../common.mjs'
import { recordVideo } from '../lib.mjs'
import { chapters } from './chapters.mjs'

const n = Number(process.argv[2])
const ch = chapters[n]
if (!ch) throw new Error('Choose a chapter from 1 to 12')
await recordVideo({ name: ch.name, scenes: ch.scenes, check: assertNoSecret, password: undefined })
