// Shared attachment validation for compose forms
(function(){
    const MAX_BYTES = 2 * 1024 * 1024;
    const allowedExt = ['jpg','jpeg','png','gif','pdf','doc','docx','ppt','pptx','txt'];

    function findFileInput(form){
        if(!form) return null;
        return form.querySelector('input[type="file"][name="attachments"]');
    }

    function validateFilesForForm(form){
        const fileInput = findFileInput(form);
        const msgEl = form ? form.querySelector('#attachmentValidation') : null;
        if(!fileInput || !fileInput.files) return true;
        if(msgEl) msgEl.textContent = '';
        for(const f of fileInput.files){
            const name = f.name || '';
            const ext = name.split('.').pop().toLowerCase();
            if(!allowedExt.includes(ext)){
                if(msgEl) msgEl.textContent = 'Unsupported file type: ' + name;
                return false;
            }
            if(f.size > MAX_BYTES){
                if(msgEl) msgEl.textContent = 'File too large: ' + name + ' (max 2 MB)';
                return false;
            }
        }
        return true;
    }

    function attachToForm(form){
        if(!form) return;
        const fileInput = findFileInput(form);
        if(fileInput){
            fileInput.addEventListener('change', function(){ validateFilesForForm(form); });
        }
        form.addEventListener('submit', function(e){
            if(!validateFilesForForm(form)){
                e.preventDefault();
                const fi = findFileInput(form);
                fi && fi.focus();
                return false;
            }
            return true;
        });
    }

    document.addEventListener('DOMContentLoaded', function(){
        // attach to the standard notice form if present
        const noticeForm = document.getElementById('noticeForm');
        if(noticeForm) attachToForm(noticeForm);

        // attach to any other forms that include attachments
        const forms = document.querySelectorAll('form');
        forms.forEach(f => {
            if(f !== noticeForm && f.querySelector('input[type="file"][name="attachments"]')){
                attachToForm(f);
            }
        });
    });
})();
