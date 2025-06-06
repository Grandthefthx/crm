// JS widget to build inline keyboard buttons on the BroadcastMessage admin page

document.addEventListener('DOMContentLoaded', function () {
    const addBtn = document.getElementById('add-button');
    const container = document.getElementById('button-builder');
    const textsInput = document.getElementById('id_button_texts');
    const urlsInput = document.getElementById('id_button_urls');
    const typesInput = document.getElementById('id_button_types');

    function updateHiddenFields() {
        const texts = [];
        const urls = [];
        const types = [];
        container.querySelectorAll('.button-row').forEach(row => {
            const text = row.querySelector('.btn-text').value;
            const url = row.querySelector('.btn-url').value;
            const type = row.querySelector('.btn-type').value;
            if (text && url && type) {
                texts.push(text);
                urls.push(url);
                types.push(type);
            }
        });
        textsInput.value = texts.join('|||');
        urlsInput.value = urls.join('|||');
        typesInput.value = types.join('|||');
    }

    function createButtonRow(text = '', url = '', type = 'url') {
        const row = document.createElement('div');
        row.className = 'button-row';
        row.innerHTML = `
            <input type="text" placeholder="Текст" class="btn-text" value="${text}" style="margin-right:5px;" />
            <input type="text" placeholder="URL/Callback" class="btn-url" value="${url}" style="margin-right:5px;" />
            <select class="btn-type" style="margin-right:5px;">
                <option value="url">url</option>
                <option value="callback">callback</option>
            </select>
            <button type="button" class="remove-btn">✖</button>
        `;
        row.querySelector('.btn-text').addEventListener('input', updateHiddenFields);
        row.querySelector('.btn-url').addEventListener('input', updateHiddenFields);
        row.querySelector('.btn-type').addEventListener('change', updateHiddenFields);
        row.querySelector('.remove-btn').addEventListener('click', () => {
            row.remove();
            updateHiddenFields();
        });
        row.querySelector('.btn-type').value = type;
        container.appendChild(row);
    }

    const savedTexts = textsInput.value ? textsInput.value.split('|||') : [];
    const savedUrls = urlsInput.value ? urlsInput.value.split('|||') : [];
    const savedTypes = typesInput.value ? typesInput.value.split('|||') : [];
    const max = Math.max(savedTexts.length, savedUrls.length, savedTypes.length);
    for (let i = 0; i < max; i++) {
        if (savedTexts[i] || savedUrls[i] || savedTypes[i]) {
            createButtonRow(savedTexts[i] || '', savedUrls[i] || '', savedTypes[i] || 'url');
        }
    }

    addBtn.addEventListener('click', function (e) {
        e.preventDefault();
        createButtonRow();
    });

    updateHiddenFields();
});
