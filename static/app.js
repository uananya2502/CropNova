// Progressive enhancement: without JavaScript all sections stay visible.
for (const form of document.querySelectorAll('[data-assessment-form]')) {
    const steps = [...form.querySelectorAll('[data-form-step]')];
    const controls = form.querySelector('[data-wizard-controls]');
    if (!steps.length || !controls) continue;
    let current = 0;
    const back = form.querySelector('[data-wizard-back]');
    const next = form.querySelector('[data-wizard-next]');
    const submit = form.querySelector('[data-wizard-submit]');
    const status = form.querySelector('[data-wizard-status]');
    const firstInvalid = (step) => [...step.querySelectorAll('input,select,textarea')]
        .find(field => !field.checkValidity());
    function showStep(index, focus = true) {
        current = index;
        steps.forEach((step, number) => { step.hidden = number !== current; });
        form.querySelectorAll('[data-step-marker]').forEach((marker, number) => {
            marker.classList.toggle('is-current', number === current);
            marker.classList.toggle('is-complete', number < current);
            if (number === current) marker.setAttribute('aria-current', 'step');
            else marker.removeAttribute('aria-current');
        });
        back.hidden = current === 0;
        next.hidden = current === steps.length - 1;
        submit.hidden = current !== steps.length - 1;
        status.textContent = `Step ${current + 1} of ${steps.length}`;
        if (focus) {
            const heading = steps[current].querySelector('h2');
            heading.tabIndex = -1;
            heading.focus({preventScroll: true});
            form.scrollIntoView({block: 'start', behavior: 'auto'});
        }
    }
    function advance() {
        const invalid = firstInvalid(steps[current]);
        if (invalid) { invalid.reportValidity(); return; }
        showStep(Math.min(current + 1, steps.length - 1));
    }
    next.addEventListener('click', advance);
    back.addEventListener('click', () => showStep(Math.max(0, current - 1)));
    form.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && current < steps.length - 1 && event.target.tagName === 'INPUT') {
            event.preventDefault();
            advance();
        }
    });
    // Native validation cannot focus a required control in a hidden section.
    // Reveal that section first, then let the browser explain the missing field.
    form.noValidate = true;
    form.addEventListener('submit', (event) => {
        const invalidStep = steps.findIndex(step => firstInvalid(step));
        if (invalidStep >= 0) {
            event.preventDefault();
            event.stopImmediatePropagation();
            showStep(invalidStep);
            firstInvalid(steps[invalidStep]).reportValidity();
        }
    }, true);
    controls.append(submit);
    controls.hidden = false;
    form.classList.add('wizard-ready');
    showStep(0, false);
}

// Keep the form understandable while the optional explanation is being written.
for (const form of document.querySelectorAll('[data-assessment-form]')) {
    form.addEventListener('submit', function () {
        const message = form.querySelector('[data-submit-status]');
        const explanation = form.querySelector('[name="use_genai"]').value === 'yes';
        message.hidden = false;
        message.textContent = explanation
            ? 'Generating your assessment and explanation. Your results will open automatically; this can take up to 30 seconds.'
            : 'Comparing your field details. Your results will open automatically…';
        form.setAttribute('aria-busy', 'true');
        for (const button of form.querySelectorAll('button[type="submit"]')) {
            button.disabled = true;
        }
    });
}
// The Back button can restore a page with its old button state.
window.addEventListener('pageshow', function () {
    for (const form of document.querySelectorAll('[data-assessment-form]')) {
        form.removeAttribute('aria-busy');
        form.querySelector('[data-submit-status]').hidden = true;
        for (const button of form.querySelectorAll('button[type="submit"]')) {
            button.disabled = false;
        }
    }
});

// Build answer elements with textContent: generated text is never treated as HTML.
for (const form of document.querySelectorAll('[data-question-form]')) {
    const output = form.parentElement.querySelector('[data-question-result]');
    const question = form.querySelector('[name="question"]');
    for (const suggestion of form.querySelectorAll('[data-question-suggestion]')) {
        suggestion.addEventListener('click', () => {
            question.value = suggestion.textContent;
            question.focus();
        });
    }
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const button = form.querySelector('[type="submit"]');
        button.disabled = true;
        form.setAttribute('aria-busy', 'true');
        output.hidden = false;
        output.textContent = 'Finding relevant evidence and writing your answer…';
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 45000);
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({question: question.value, crop_id: form.elements.crop_id.value}),
                signal: controller.signal,
            });
            const result = await response.json();
            output.replaceChildren();
            const answer = document.createElement('p');
            answer.textContent = result.answer || 'We could not answer this question. Please try again.';
            output.append(answer);
            for (const record of result.evidence || []) {
                const card = document.createElement('article');
                card.className = 'question-evidence';
                const heading = document.createElement('h3');
                heading.textContent = record.title;
                const text = document.createElement('p');
                text.textContent = record.text;
                card.append(heading, text);
                for (const source of record.sources || []) {
                    // Only links from recorded source metadata can become anchors.
                    if (!/^https?:\/\//i.test(source.url || '')) continue;
                    const link = document.createElement('a');
                    link.href = source.url;
                    link.textContent = source.title || 'Read the source';
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    card.append(link);
                }
                output.append(card);
            }
            if (result.status === 'answered') {
                const note = document.createElement('small');
                note.textContent = 'Written from the findings shown above. Confirm local conditions before planting.';
                output.append(note);
            }
        } catch (error) {
            output.textContent = 'The answer could not be loaded. Please try again. Your recorded crop findings are available below.';
        } finally {
            clearTimeout(timeout);
            button.disabled = false;
            form.removeAttribute('aria-busy');
        }
    });
}

// Keep district choices in sync and preview the actual four checks before submit.
for (const form of document.querySelectorAll('[data-assessment-form]')) {
    const state = form.elements.state;
    const district = form.elements.district;
    const crop = form.elements.candidate_ids;
    const preview = form.querySelector('[data-coverage-preview]');
    let catalogue = null;
    let timer = null;
    let currentRequest = null;

    function updateDistricts(preserveCurrent) {
        if (!catalogue) {
            if (!preserveCurrent) district.replaceChildren(new Option('Not specified (optional)', ''));
            return;
        }
        const previous = preserveCurrent ? district.value : '';
        const choices = catalogue.districts[state.value] || [];
        district.replaceChildren(new Option('Not specified (optional)', ''));
        for (const name of choices) district.add(new Option(name, name));
        if (previous && !choices.includes(previous)) {
            district.add(new Option(previous + ' — saved district', previous));
        }
        district.value = previous;
        const hint = form.querySelector('#district-help');
        hint.textContent = choices.length
            ? 'Optional location label. District names do not establish district-specific crop guidance.'
            : 'District menus currently cover Haryana, Rajasthan and Punjab. You can leave this optional field unspecified.';
    }

    async function updatePreview() {
        if (currentRequest) currentRequest.abort();
        currentRequest = null;
        if (!state.value || !crop.value) {
            preview.replaceChildren('Select a state and a crop to check the available references.');
            preview.dataset.state = '';
            return;
        }
        const controller = new AbortController();
        currentRequest = controller;
        preview.dataset.state = '';
        preview.textContent = 'Checking the references for these selections…';
        const timeout = setTimeout(() => controller.abort(), 10000);
        try {
            const response = await fetch('/coverage-preview', {
                method: 'POST',
                headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                body: new URLSearchParams(new FormData(form)),
                signal: controller.signal,
            });
            if (!response.ok) throw new Error('Preview unavailable');
            const result = await response.json();
            if (currentRequest !== controller) return;
            preview.replaceChildren();
            preview.dataset.state = result.state;
            const title = document.createElement('strong');
            title.textContent = result.title;
            preview.append(title);
            for (const message of result.messages || []) {
                const paragraph = document.createElement('p');
                paragraph.textContent = message;
                preview.append(paragraph);
            }
            for (const candidate of result.crops || []) {
                const line = document.createElement('p');
                line.textContent = `${candidate.name}: ${candidate.matched} of ${candidate.total} checks match.`;
                preview.append(line);
                const remaining = candidate.checks.filter(check => check.status !== 'satisfied');
                if (!remaining.length) continue;
                const list = document.createElement('ul');
                for (const check of remaining) {
                    const item = document.createElement('li');
                    item.textContent = `${check.name}: ${check.reason}`;
                    list.append(item);
                }
                preview.append(list);
            }
        } catch (error) {
            if (currentRequest !== controller) return;
            preview.textContent = 'The preview could not be loaded. You can still generate an assessment or use a covered reference profile.';
        } finally {
            clearTimeout(timeout);
        }
    }

    form.addEventListener('change', (event) => {
        if (event.target === state) updateDistricts(false);
        clearTimeout(timer);
        timer = setTimeout(updatePreview, 200);
    });
    fetch('/form-options')
        .then(response => {
            if (!response.ok) throw new Error('Choices unavailable');
            return response.json();
        })
        .then(data => {
            catalogue = data;
            updateDistricts(true);
        })
        .catch(() => {
            // The server-rendered choices remain usable without this enhancement.
        });
    updatePreview();
}
