// Run against the installed release artifact: node tests/test_emscripten.cjs dist/ocl.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

async function main() {
  const filename = process.argv[2];
  assert.ok(filename, 'Pass the path to the built ocl.js');

  // The artifact targets browsers. Run it without Node globals in a VM,
  // using the real WebAssembly runtime to exercise its compiled bindings.
  const context = vm.createContext({
    console, WebAssembly, TextDecoder, TextEncoder, atob, btoa,
    setTimeout, clearTimeout, performance,
    window: {},
    document: { currentScript: { src: 'http://localhost/ocl.js' } },
  });
  vm.runInContext(fs.readFileSync(filename, 'utf8'), context, { filename });
  const ocl = await context.ocl();

  const point = new ocl.Point(3, 4, 0);
  assert.equal(point.norm(), 5);
  point.delete();

  const cutter = new ocl.BatchPushCutter();
  cutter.setThreads(1);
  assert.equal(cutter.getThreads(), 1);
  cutter.setBucketSize(8);
  assert.equal(cutter.getBucketSize(), 8);
  cutter.setXDirection();
  cutter.setYDirection();
  cutter.delete();

  const waterline = new ocl.Waterline();
  waterline.setZ(1);
  const loops = waterline.getLoops();
  assert.equal(loops.size(), 0);
  loops.delete();
  waterline.delete();

  console.log('PASS: Emscripten module initialization and geometry/cutter bindings');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
