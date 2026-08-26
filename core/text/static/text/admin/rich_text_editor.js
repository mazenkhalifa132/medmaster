import { Editor, Node } from 'https://esm.sh/@tiptap/core@2.11.5';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2.11.5';
import Underline from 'https://esm.sh/@tiptap/extension-underline@2.11.5';
import Link from 'https://esm.sh/@tiptap/extension-link@2.11.5';
import Image from 'https://esm.sh/@tiptap/extension-image@2.11.5';
import TextAlign from 'https://esm.sh/@tiptap/extension-text-align@2.11.5';
import Highlight from 'https://esm.sh/@tiptap/extension-highlight@2.11.5';
import TextStyle from 'https://esm.sh/@tiptap/extension-text-style@2.11.5';
import Color from 'https://esm.sh/@tiptap/extension-color@2.11.5';
import Table from 'https://esm.sh/@tiptap/extension-table@2.11.5';
import TableRow from 'https://esm.sh/@tiptap/extension-table-row@2.11.5';
import TableHeader from 'https://esm.sh/@tiptap/extension-table-header@2.11.5';
import TableCell from 'https://esm.sh/@tiptap/extension-table-cell@2.11.5';

const csrfToken = () => document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
const SOURCE_SYNC_DELAY = 350;
const calloutLabels = {
    'medical-key-point': 'Key Point', 'medical-clinical-pearl': 'Clinical Pearl',
    'medical-warning': 'Important', 'medical-clinical-case': 'Clinical Case',
    'medical-definition': 'Definition', 'medical-diagnosis': 'Diagnosis',
    'medical-treatment': 'Treatment', 'medical-pathophysiology': 'Pathophysiology',
};
const MedicalCallout = Node.create({
    name: 'medicalCallout', group: 'block', content: 'block+', defining: true,
    addAttributes() { return { class: { default: 'medical-callout medical-key-point' } }; },
    parseHTML() { return [{ tag: 'aside.medical-callout' }]; },
    renderHTML({ HTMLAttributes }) { return ['aside', HTMLAttributes, 0]; },
});

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.rich-text-editor').forEach((root) => {
        // The admin can re-render widgets; avoid duplicate editor instances.
        if (root.dataset.initialized === 'true') return;
        root.dataset.initialized = 'true';

        const source = root.querySelector('.rich-text-editor-source');
        const canvas = root.querySelector('.rich-text-editor__canvas');
        const status = root.querySelector('.rich-text-editor__status');
        const setStatus = (message) => { status.textContent = message; };
        let sourceSyncTimer;
        const syncSource = () => {
            window.clearTimeout(sourceSyncTimer);
            source.value = editor.getHTML();
        };
        const scheduleSourceSync = () => {
            window.clearTimeout(sourceSyncTimer);
            sourceSyncTimer = window.setTimeout(syncSource, SOURCE_SYNC_DELAY);
        };
        const editor = new Editor({
            element: canvas,
            content: source.value,
            extensions: [
                StarterKit, Underline, TextStyle, Color, Highlight.configure({ multicolor: true }),
                Link.configure({ openOnClick: false }), Image, TextAlign.configure({ types: ['heading', 'paragraph'] }),
                Table.configure({ resizable: true }), TableRow, TableHeader, TableCell, MedicalCallout,
            ],
            onUpdate: () => {
                // Avoid serializing an entire long document on every keystroke.
                scheduleSourceSync();
                setStatus('Unsaved changes');
            },
        });
        root.closest('form').addEventListener('submit', () => { source.value = editor.getHTML(); setStatus('Saving…'); });

        const moveToParagraphAfterCurrentTable = () => {
            const { $from } = editor.state.selection;
            for (let depth = $from.depth; depth > 0; depth -= 1) {
                if ($from.node(depth).type.name !== 'table') continue;

                const tableEnd = $from.after(depth);
                const nextNode = editor.state.doc.nodeAt(tableEnd);
                if (nextNode?.type.name === 'paragraph') {
                    editor.commands.focus(tableEnd + 1);
                } else {
                    editor.chain()
                        .insertContentAt(tableEnd, { type: 'paragraph' })
                        .focus(tableEnd + 1)
                        .run();
                }
                setStatus('Ready to write below the table.');
                return true;
            }
            setStatus('Place the cursor in a table first.');
            return false;
        };

        canvas.addEventListener('blur', syncSource);

        const uploadImage = async (file) => {
            if (!file) return;
            if (!file.type.startsWith('image/') || file.size > 5 * 1024 * 1024) {
                setStatus('Choose an image under 5 MB (JPG, PNG, GIF, or WebP).'); return;
            }
            setStatus('Uploading image…');
            const data = new FormData(); data.append('image', file);
            try {
                const response = await fetch(root.dataset.uploadUrl, {
                    method: 'POST', body: data, credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken() },
                });
                const payload = await response.json().catch(() => ({}));
                if (!response.ok || !payload.url) {
                    setStatus(payload.error || 'Image upload failed. Please try again.');
                    return;
                }
                editor.chain().focus().setImage({ src: payload.url, alt: file.name }).run();
                setStatus('Image uploaded. Unsaved changes');
            } catch (error) {
                setStatus('Image upload failed. Check your connection and try again.');
            }
        };
        canvas.addEventListener('drop', (event) => { const file = event.dataTransfer.files[0]; if (file) { event.preventDefault(); uploadImage(file); } });
        canvas.addEventListener('dragover', (event) => event.preventDefault());
        canvas.addEventListener('paste', (event) => {
            const image = [...event.clipboardData.files].find(file => file.type.startsWith('image/'));
            if (image) {
                event.preventDefault();
                uploadImage(image);
            }
        });

        root.querySelectorAll('button[data-command]').forEach((control) => {
            // Keep the text selection active. Without this, clicking a toolbar
            // button moves focus away from TipTap before its command can run.
            control.addEventListener('mousedown', (event) => event.preventDefault());
            control.addEventListener('click', (event) => {
            event.preventDefault();
            const command = control.dataset.command;
            const chain = editor.chain().focus();
            if (command === 'bold') chain.toggleBold().run();
            else if (command === 'italic') chain.toggleItalic().run();
            else if (command === 'underline') chain.toggleUnderline().run();
            else if (command === 'bulletList') chain.toggleBulletList().run();
            else if (command === 'orderedList') chain.toggleOrderedList().run();
            else if (command === 'blockquote') chain.toggleBlockquote().run();
            else if (command === 'horizontalRule') chain.setHorizontalRule().run();
            else if (command === 'undo') chain.undo().run();
            else if (command === 'redo') chain.redo().run();
            else if (command === 'highlight') chain.toggleHighlight({ color: '#fef08a' }).run();
            else if (command === 'table') {
                const rows = Number.parseInt(window.prompt('Number of rows (1-20)', '3'), 10);
                const cols = Number.parseInt(window.prompt('Number of columns (1-20)', '3'), 10);
                if (!Number.isInteger(rows) || !Number.isInteger(cols) || rows < 1 || cols < 1 || rows > 20 || cols > 20) {
                    setStatus('Enter between 1 and 20 rows and columns.');
                    return;
                }
                chain.insertTable({ rows, cols, withHeaderRow: true }).run();
                moveToParagraphAfterCurrentTable();
            }
            else if (command === 'addRowBefore') chain.addRowBefore().run();
            else if (command === 'addRowAfter') chain.addRowAfter().run();
            else if (command === 'deleteRow') chain.deleteRow().run();
            else if (command === 'addColumnBefore') chain.addColumnBefore().run();
            else if (command === 'addColumnAfter') chain.addColumnAfter().run();
            else if (command === 'deleteColumn') chain.deleteColumn().run();
            else if (command === 'deleteTable') chain.deleteTable().run();
            else if (command === 'deleteBlock') {
                if (editor.isActive('table')) chain.deleteTable().run();
                else if (editor.isActive('medicalCallout')) chain.deleteNode('medicalCallout').run();
                else setStatus('Place the cursor in a table or medical block before deleting it.');
            }
            else if (command === 'paragraphBelowTable') moveToParagraphAfterCurrentTable();
            else if (command === 'link') { const href = window.prompt('Link URL'); if (href) chain.extendMarkRange('link').setLink({ href }).run(); }
            else if (command === 'image') { const picker = document.createElement('input'); picker.type = 'file'; picker.accept = 'image/jpeg,image/png,image/gif,image/webp'; picker.onchange = () => uploadImage(picker.files[0]); picker.click(); }
            });
        });
        root.querySelectorAll('select[data-command], input[data-command="color"]').forEach((control) => control.addEventListener('change', () => {
            const value = control.value; const command = control.dataset.command; const chain = editor.chain().focus();
            if (command === 'heading') value === '0' ? chain.setParagraph().run() : chain.toggleHeading({ level: Number(value) }).run();
            else if (command === 'align') chain.setTextAlign(value).run();
            else if (command === 'color') chain.setColor(value).run();
            else if (command === 'tableAction' && value) {
                const canRun = editor.can();
                if (typeof canRun[value] === 'function' && canRun[value]()) chain[value]().run();
                else setStatus('Place the cursor in a table before using table actions.');
                control.value = '';
            }
            else if (command === 'callout' && value) {
                chain.insertContent(`<aside class="medical-callout ${value}"><p><strong>${calloutLabels[value]}</strong></p><p>Write your content here.</p></aside><p></p>`).run();
                control.value = '';
            }
        }));
    });
});
