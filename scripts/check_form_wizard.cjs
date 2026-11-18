/* Unit-check progressive form navigation without a browser or network access. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
function element() {
    return {
        hidden: false, listeners: {}, attrs: {}, classes: new Set(),
        addEventListener(name, callback) { this.listeners[name] = callback; },
        setAttribute(name, value) { this.attrs[name] = value; },
        removeAttribute(name) { delete this.attrs[name]; },
        append(child) { this.appended = child; },
        focus() {}, scrollIntoView() {},
        classList: {add() {}, toggle() {}},
    };
}
const state = {valid: false, disabled: false, reports: 0,
    checkValidity() { return this.valid; }, reportValidity() { this.reports++; }};
const crop = {...state, valid: true, reports: 0};
const soil = {...state, valid: true, reports: 0};
const fields = [state, soil, crop];
const steps = fields.map((field, index) => {
    const step = element();
    step.querySelectorAll = () => [field];
    step.querySelector = () => element();
    return step;
});
const markers = steps.map(element);
const controls = element(), back = element(), next = element();
const submit = element(), status = element(), form = element();
form.querySelectorAll = (selector) => selector === '[data-form-step]' ? steps : markers;
const elements = {'[data-wizard-controls]':controls, '[data-wizard-back]':back,
    '[data-wizard-next]':next, '[data-wizard-submit]':submit, '[data-wizard-status]':status};
form.querySelector = (selector) => elements[selector];
const code = fs.readFileSync('static/app.js', 'utf8').split('// Keep the form understandable')[0];
vm.runInNewContext(code, {document:{querySelectorAll: () => [form]}});
assert.equal(form.noValidate, true);
assert.deepEqual(steps.map(s => s.hidden), [false,true,true]);
next.listeners.click();
assert.equal(state.reports,1);
assert.equal(steps[0].hidden,false);
state.valid=true;
next.listeners.click();
assert.deepEqual(steps.map(s => s.hidden), [true,false,true]);
next.listeners.click();
assert.deepEqual(steps.map(s => s.hidden), [true,true,false]);
assert.equal(submit.hidden,false);
assert.equal(next.hidden,true);
back.listeners.click();
assert.equal(steps[1].hidden,false);
assert.equal(submit.hidden,true);
crop.valid=false;
const invalid = {prevented:false, stopped:false,
    preventDefault(){this.prevented=true}, stopImmediatePropagation(){this.stopped=true}};
form.listeners.submit(invalid);
assert.equal(invalid.prevented,true);
assert.equal(invalid.stopped,true);
assert.equal(steps[2].hidden,false);
assert.equal(crop.reports,1);
crop.valid=true;
const valid={preventDefault(){throw Error('A valid form must submit')},stopImmediatePropagation(){}};
form.listeners.submit(valid);
assert(fields.every(f => f.disabled === false));
back.listeners.click(); back.listeners.click();
const enter={key:'Enter',target:{tagName:'INPUT'},preventDefault(){this.prevented=true}};
form.listeners.keydown(enter);
assert.equal(enter.prevented,true);
assert.equal(steps[1].hidden,false);
console.log('Wizard checks passed: staged navigation, validation, Back, Enter, and complete field retention.');
