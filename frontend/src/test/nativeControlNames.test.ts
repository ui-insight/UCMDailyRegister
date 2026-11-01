import ts from 'typescript';
import { expect, it } from 'vitest';

// Check authored JSX without depending on whichever branch a fixture renders.
// Runtime tests still verify focus, labels and states in representative flows.
const sources = import.meta.glob('../**/*.tsx', { query: '?raw', import: 'default', eager: true });
for (const [file, text] of Object.entries(sources)) {
  if (file.endsWith('.test.tsx') || typeof text !== 'string') continue;
  it(`${file} keeps native fields named and excludes known failing solid fills`, () => {
    const source = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    const fields: ts.Node[] = [];
    const labels = new Set<string>();
    const attributes = (opening: ts.JsxOpeningElement | ts.JsxSelfClosingElement) => {
      const entries = opening.attributes.properties.filter(ts.isJsxAttribute).map((attr) => {
        const value = attr.initializer;
        return [attr.name.getText(source), value && ts.isStringLiteral(value) ? value.text
          : value && ts.isJsxExpression(value) ? value.expression?.getText(source) : undefined];
      });
      return Object.fromEntries(entries) as Record<string, string | undefined>;
    };
    function collect(node: ts.Node) {
      const opening = ts.isJsxElement(node) ? node.openingElement : ts.isJsxSelfClosingElement(node) ? node : null;
      if (opening) {
        const tag = opening.tagName.getText(source);
        if (tag === 'label') {
          const id = attributes(opening).htmlFor;
          if (id) labels.add(id);
        }
        if (['input', 'textarea', 'select'].includes(tag)) fields.push(node);
      }
      ts.forEachChild(node, collect);
    }
    collect(source);
    // These enabled normal-text pairings have measured contrast below 4.5:1.
    const failingFills: string[] = [];
    function checkFills(node: ts.Node) {
      if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
        if (/\bbg-ui-gold-[56]00\b/.test(node.text) && /\btext-white\b/.test(node.text)) failingFills.push(node.text);
        if (/\bbg-status-(info|edited|warning|success|attention|error)-500\b/.test(node.text) && /\btext-white\b/.test(node.text)) failingFills.push(node.text);
      }
      ts.forEachChild(node, checkFills);
    }
    checkFills(source);
    expect(failingFills).toEqual([]);
    const unnamed: number[] = [];
    for (const field of fields) {
      const opening = ts.isJsxElement(field) ? field.openingElement : field as ts.JsxSelfClosingElement;
      const attrs = attributes(opening);
      if (attrs.type === 'hidden' || attrs['aria-label'] || attrs['aria-labelledby'] || (attrs.id && labels.has(attrs.id))) continue;
      let parent = field.parent;
      while (parent && !(ts.isJsxElement(parent) && parent.openingElement.tagName.getText(source) === 'label')) parent = parent.parent;
      if (!parent) unnamed.push(source.getLineAndCharacterOfPosition(field.getStart()).line + 1);
    }
    expect(unnamed, `Unlabelled native fields at lines ${unnamed.join(', ')}`).toEqual([]);
  });
}
