import asyncio,json,os,hashlib,shutil
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('PROTEIN_MOTION_TEST_OUTPUT',str(ROOT/'test-output')));OUT.mkdir(parents=True,exist_ok=True)
async def main():
 async with async_playwright() as p:
  options={'headless':True,'args':['--no-sandbox']}
  chrome=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
  if chrome: options['executable_path']=chrome
  browser=await p.chromium.launch(**options)
  page=await browser.new_page(viewport={'width':1280,'height':1000},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(os.environ.get('PROTEIN_MOTION_BASE_URL','http://127.0.0.1:8765/'),wait_until='networkidle')
  await page.locator('#play-toggle').wait_for(state='visible')
  await page.wait_for_function("!document.getElementById('play-toggle').disabled")
  checks=[]
  async def check(name,passed,extra=None):
   assert passed,(name,extra);checks.append({'case':name,'passed':True,'detail':extra})
  await check('real trajectory loaded',await page.locator('#frame-counter').inner_text()=='01 / 51',await page.locator('#frame-counter').inner_text())
  await page.locator('#timeline').fill('50');await page.locator('#timeline').dispatch_event('input')
  expected=json.loads((ROOT/'data/demo.json').read_text())['frames'][-1]['rmsd_angstrom']
  displayed=float(await page.locator('#rmsd-value').inner_text())
  await check('frame scrub synchronizes RMSD',abs(displayed-expected)<0.001,{'displayed':displayed,'expected':expected})
  await page.locator('#timeline').fill('0');await page.locator('#timeline').dispatch_event('input')
  await page.locator('#play-toggle').click();await page.wait_for_timeout(450);await page.locator('#play-toggle').click()
  await check('playback advances frames',int(await page.locator('#timeline').input_value())>0)
  canvas=page.locator('#molecule-canvas');before=hashlib.sha256(await canvas.screenshot()).hexdigest();box=await canvas.bounding_box()
  await page.mouse.move(box['x']+box['width']*.5,box['y']+box['height']*.5);await page.mouse.down();await page.mouse.move(box['x']+box['width']*.7,box['y']+box['height']*.6,steps=8);await page.mouse.up()
  after=hashlib.sha256(await canvas.screenshot()).hexdigest();await check('drag rotates rendered backbone',before!=after)
  await page.locator('#reset-view').click()
  async with page.expect_download() as pending:await page.locator('#export-csv').click()
  download=await pending.value;target=OUT/'protein-motion-measurements.csv';await download.save_as(target)
  csv=target.read_text().splitlines();await check('CSV includes every frame and units',len(csv)==52 and 'ca_rmsd_angstrom' in csv[0],{'lines':len(csv)})
  for width in [320,736,1280]:
   await page.set_viewport_size({'width':width,'height':1000})
   await page.locator('#provenance').evaluate('(el)=>el.open=true')
   await page.wait_for_timeout(100)
   sizes=await page.evaluate('({w:innerWidth,s:document.documentElement.scrollWidth})')
   await check(f'no horizontal overflow at {width}px',sizes['s']<=sizes['w'],sizes)
  await page.locator('#provenance').evaluate('(el)=>el.open=false');await page.set_viewport_size({'width':1280,'height':1000});await page.screenshot(path=str(OUT/'protein-motion-desktop.png'),full_page=True)
  await page.set_viewport_size({'width':390,'height':844});await page.screenshot(path=str(OUT/'protein-motion-mobile.png'),full_page=True)
  await check('no browser runtime exceptions',not errors,errors)
  print(json.dumps({'checks':checks,'screenshots':str(OUT)},indent=2))
  (ROOT/'docs/browser-validation.json').write_text(json.dumps({'checks':checks,'scope':'Browser interactions against the bundled real short CPU trajectory. No clinical or long-run MD validation.'},indent=2)+'\n')
  await browser.close()
asyncio.run(main())
