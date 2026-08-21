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
        const source = root.querySelector('.rich-text-editor-source');
        const canvas = root.querySelector('.rich-text-editor__canvas');
        const status = root.querySelector('.rich-text-editor__status');
        const setStatus = (message) => { status.textContent = message; };
        const editor = new Editor({
            element: canvas,
            content: source.value,
            extensions: [
                StarterKit, Underline, TextStyle, Color, Highlight.configure({ multicolor: true }),
                Link.configure({ openOnClick: false }), Image, TextAlign.configure({ types: ['heading', 'paragraph'] }),
                Table.configure({ resizable: true }), TableRow, TableHeader, TableCell, MedicalCallout,
            ],
            onUpdate: ({ editor: current }) => {
                source.value = current.getHTML();
                setStatus('Ready to save');
            },
        });
        root.closest('form').addEventListener('submit', () => { source.value = editor.getHTML(); setStatus('Saving…'); });

        const uploadImage = async (file) => {
            if (!file) return;
            if (!file.type.startsWith('image/') || file.size > 5 * 1024 * 1024) {
                setStatus('Choose an image under 5 MB (JPG, PNG, GIF, or WebP).'); return;
            }
            setStatus('Uploading image…');
            const data = new FormData(); data.append('image', file);
            const response = await fetch(root.dataset.uploadUrl, {
                method: 'POST', body: data, credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken() },
            });
            const payload = await response.json();
            if (!response.ok) { setStatus(payload.error || 'Image upload failed.'); return; }
            editor.chain().focus().setImage({ src: payload.url, alt: file.name }).run();
            setStatus('Image uploaded. Ready to save');
        };
        canvas.addEventListener('drop', (event) => { const file = event.dataTransfer.files[0]; if (file) { event.preventDefault(); uploadImage(file); } });
        canvas.addEventListener('dragover', (event) => event.preventDefault());

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
            else if (command === 'table') chain.insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
            else if (command === 'link') { const href = window.prompt('Link URL'); if (href) chain.extendMarkRange('link').setLink({ href }).run(); }
            else if (command === 'image') { const picker = document.createElement('input'); picker.type = 'file'; picker.accept = 'image/jpeg,image/png,image/gif,image/webp'; picker.onchange = () => uploadImage(picker.files[0]); picker.click(); }
            });
        });
        root.querySelectorAll('select[data-command], input[data-command="color"]').forEach((control) => control.addEventListener('change', () => {
            const value = control.value; const command = control.dataset.command; const chain = editor.chain().focus();
            if (command === 'heading') value === '0' ? chain.setParagraph().run() : chain.toggleHeading({ level: Number(value) }).run();
            else if (command === 'align') chain.setTextAlign(value).run();
            else if (command === 'color') chain.setColor(value).run();
            else if (command === 'callout' && value) {
                chain.insertContent(`<aside class="medical-callout ${value}"><strong>${calloutLabels[value]}</strong><p>Write your content here.</p></aside><p></p>`).run();
                control.value = '';
            }
        }));
    });
});
