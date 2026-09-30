// NODE_PATH=./scratch/web-test/node_modules node viewer/smoke.cjs
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto('http://127.0.0.1:8765/');
    await page.waitForFunction(()=>document.body.dataset.ready==='true',null,{timeout:60000});
    assert.equal(await page.locator('[data-part]').count(),14);
    const resources=await page.evaluate(()=>performance.getEntriesByType('resource').map(r=>({url:r.name,bytes:r.encodedBodySize})));
    assert.ok(resources.every(r=>!new URL(r.url).pathname.startsWith('/print/')),'Print STLs should download only on request');
    assert.ok(resources.reduce((sum,r)=>sum+r.bytes,0)<8_000_000,'Viewer payload exceeds 8 MB');
    assert.equal((await page.evaluate(()=>viewerPerf())).sharedPrintGeometry,true);
    const idleFrames=await page.evaluate(()=>viewerPerf().frames);
    await page.waitForTimeout(150);
    assert.equal((await page.evaluate(()=>viewerPerf())).frames,idleFrames,'Viewer renders while idle');
    assert.equal((await page.evaluate(()=>viewerState())).visible,14);
    await page.locator('[data-part="pot"]').uncheck();
    assert.equal((await page.evaluate(()=>viewerState())).visible,13);
    await page.getByRole('button',{name:'Side',exact:true}).click();
    assert.equal((await page.evaluate(()=>viewerState())).view,'side');
    for(const distance of [230,250,270,290,310]){
      await page.locator('#distance').selectOption(String(distance));
      const state=await page.evaluate(()=>viewerState());
      assert.equal(state.distance,distance);
      assert.equal(state.potShift,distance-250);
      assert.equal(state.guideShift,distance-250);
      assert.equal(state.lightShift,distance-250);
      assert.equal(state.puckShift,distance-250);
      assert.equal(state.cameraShift,0);
    }
    await page.locator('#explode').fill('75');
    assert.equal((await page.evaluate(()=>viewerState())).explode,75);
    assert.equal((await page.evaluate(()=>viewerState())).guides,false);
    assert.equal((await page.evaluate(()=>viewerState())).potShift,60+35*.75);
    await page.getByRole('button',{name:'Reset',exact:true}).click();
    assert.deepEqual(await page.evaluate(()=>viewerState()),{parts:14,visible:14,view:'iso',explode:0,guides:true,distance:250,potShift:0,cameraShift:0,guideShift:0,lightShift:0,puckShift:0});
    for(const file of ['assembly.step','print/pot.stl','print/m3_pilot_coupon.stl'])assert.equal((await page.request.head('http://127.0.0.1:8765/'+file)).status(),200);
    await page.screenshot({path:path.resolve(__dirname,'../scratch/viewer-desktop.png')});
    await page.getByRole('button',{name:'Bed',exact:true}).click();
    assert.equal(await page.locator('#assembly-controls').isVisible(),false);
    const expected=[['camera_base'],['plant_base'],['pot','catch_tray','camera_shoe','ruler_shoe','camera_mast','ruler_support'],['growth_ruler'],['light_arm','light_cradle'],['m3_pilot_coupon']];
    const sizes=JSON.parse(require('node:fs').readFileSync(path.resolve(__dirname,'../output/validation.json'),'utf8')).parts;
    for(let plate=0;plate<expected.length;plate++){
      await page.locator('#plate').selectOption(String(plate));
      const state=await page.evaluate(()=>bedState());
      assert.equal(state.mode,'bed');assert.equal(state.plate,plate);assert.equal(state.fits,true);
      assert.equal(state.assemblyVisible,false);assert.equal(state.bedVisible,true);
      assert.deepEqual(state.parts.map(p=>p.name),expected[plate]);
      for(const part of state.parts){
        assert.ok(Math.abs(part.min[2])<.001);
        assert.ok(part.min[0]>=5&&part.min[1]>=5&&part.max[0]<=245&&part.max[1]<=205&&part.max[2]<=210);
        if(part.name==='light_arm')assert.ok(part.max[2]<8.01);
        if(part.name==='camera_mast')assert.ok(part.max[2]<11.4);
        if(part.name==='ruler_support')assert.ok(part.max[2]<5.01);
        if(part.name.endsWith('_shoe'))assert.ok(part.max[2]<30.01);
        if(sizes[part.name])sizes[part.name].print_size_mm.forEach((size,axis)=>assert.ok(Math.abs(part.max[axis]-part.min[axis]-size)<.02));
      }
      for(let i=0;i<state.parts.length;i++)for(let j=i+1;j<state.parts.length;j++)assert.ok([0,1].some(axis=>state.parts[i].max[axis]+10<=state.parts[j].min[axis]||state.parts[j].max[axis]+10<=state.parts[i].min[axis]));
      for(const link of await page.locator('#bed-parts a').all())assert.equal((await page.request.head(new URL(await link.getAttribute('href'),page.url()).href)).status(),200);
      await page.getByRole('button',{name:'Top',exact:true}).click();
      await page.screenshot({path:path.resolve(__dirname,`../scratch/viewer-bed-${plate+1}.png`)});
    }
    await page.getByRole('button',{name:'Reset',exact:true}).click();
    assert.equal((await page.evaluate(()=>bedState())).plate,0);
    await page.locator('#plate').selectOption('2');
    await page.getByRole('button',{name:'Orbit',exact:true}).click();
    await page.screenshot({path:path.resolve(__dirname,'../scratch/viewer-bed-flat-mounts.png')});
    await page.getByRole('button',{name:'Assembly',exact:true}).click();
    assert.equal((await page.evaluate(()=>bedState())).assemblyVisible,true);
    assert.equal((await page.evaluate(()=>viewerState())).distance,250);
    await page.setViewportSize({width:390,height:844});
    await page.getByRole('button',{name:'Top',exact:true}).click();
    assert.equal((await page.evaluate(()=>viewerState())).view,'top');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:path.resolve(__dirname,'../scratch/viewer-mobile.png'),fullPage:true});
    await page.goto('http://127.0.0.1:8765/#bed');
    await page.waitForFunction(()=>document.body.dataset.ready==='true',null,{timeout:60000});
    assert.equal((await page.evaluate(()=>bedState())).mode,'bed');
    await page.locator('#plate').selectOption('2');
    await page.getByRole('button',{name:'Top',exact:true}).click();
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:path.resolve(__dirname,'../scratch/viewer-bed-mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('PASS: assembly controls, six print plates, STL dimensions/orientations, bed bounds/spacing, mode switching, reset, downloads, direct bed URL, mobile layout; no browser errors.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
