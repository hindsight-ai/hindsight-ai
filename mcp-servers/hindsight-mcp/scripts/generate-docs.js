#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '..', 'docs', 'client-config.json');
const README_PATH = path.join(__dirname, '..', 'README.md');
const START_MARKER = '<!-- GENERATED:CLIENT_SETUP -->';
const END_MARKER = '<!-- END GENERATED:CLIENT_SETUP -->';

function loadConfig() {
  if (!fs.existsSync(CONFIG_PATH)) {
    throw new Error(`Config file not found: ${CONFIG_PATH}`);
  }
  const raw = fs.readFileSync(CONFIG_PATH, 'utf8');
  return JSON.parse(raw);
}

function renderSummary(summaryClients = []) {
  if (!Array.isArray(summaryClients) || summaryClients.length === 0) {
    return '';
  }

  const rows = summaryClients
    .map((client) => `| ${client.name} | ${client.method} | ${client.format} | ${client.location} |`)
    .join('\n');

  return [
    '<details>',
    '<summary>Configuration summary (selected clients)</summary>',
    '',
    '| Client | Configuration method | Format | Default location |',
    '| --- | --- | --- | --- |',
    rows,
    '',
    '</details>'
  ].join('\n');
}

function renderSteps(steps = []) {
  if (!Array.isArray(steps) || steps.length === 0) {
    return '';
  }
  return steps.map((step, index) => `${index + 1}. ${step}`).join('\n');
}

function renderCodeSamples(codeSamples = []) {
  if (!Array.isArray(codeSamples) || codeSamples.length === 0) {
    return '';
  }
  return codeSamples
    .map((sample) => {
      const lang = sample.language || '';
      const code = sample.code || '';
      return ['```' + lang, code, '```'].join('\n');
    })
    .join('\n\n');
}

function renderNotes(notes = []) {
  if (!Array.isArray(notes) || notes.length === 0) {
    return '';
  }
  return notes.map((note) => `- ${note}`).join('\n');
}

function renderClientSection(client) {
  const lines = [`### ${client.name}`, '', '<details>', '<summary>Show instructions</summary>', ''];

  if (client.intro) {
    lines.push(client.intro.trim());
    lines.push('');
  }

  const steps = renderSteps(client.steps);
  if (steps) {
    lines.push(steps);
    lines.push('');
  }

  const code = renderCodeSamples(client.codeSamples);
  if (code) {
    lines.push(code);
    lines.push('');
  }

  const notes = renderNotes(client.notes);
  if (notes) {
    lines.push(notes);
    lines.push('');
  }

  while (lines.length && lines[lines.length - 1] === '') {
    lines.pop();
  }

  lines.push('</details>');
  return lines.join('\n');
}

function renderClientSections(clients = []) {
  if (!Array.isArray(clients) || clients.length === 0) {
    return '';
  }
  return clients.map(renderClientSection).join('\n\n');
}

function renderAdditionalSections(sections = []) {
  if (!Array.isArray(sections) || sections.length === 0) {
    return '';
  }

  return sections
    .map((section) => {
      const lines = [`### ${section.title}`, ''];
      (section.blocks || []).forEach((block) => {
        if (block.type === 'paragraph') {
          lines.push(block.text.trim());
          lines.push('');
        } else if (block.type === 'list') {
          (block.items || []).forEach((item) => {
            lines.push(`- ${item}`);
          });
          lines.push('');
        } else if (block.type === 'code') {
          const lang = block.language || '';
          const code = block.code || '';
          lines.push('```' + lang);
          lines.push(code);
          lines.push('```');
          lines.push('');
        }
      });
      while (lines.length && lines[lines.length - 1] === '') {
        lines.pop();
      }
      return lines.join('\n');
    })
    .join('\n\n');
}

function buildGeneratedContent(config) {
  const parts = [];

  const summary = renderSummary(config.summaryClients);
  if (summary) {
    parts.push(summary);
  }

  const clientSections = renderClientSections(config.clients);
  if (clientSections) {
    parts.push(clientSections);
  }

  const additional = renderAdditionalSections(config.additionalSections);
  if (additional) {
    parts.push(additional);
  }

  return parts.join('\n\n');
}

function injectContent(readme, generated) {
  const startIndex = readme.indexOf(START_MARKER);
  const endIndex = readme.indexOf(END_MARKER);

  if (startIndex === -1 || endIndex === -1) {
    throw new Error('README markers for generated content not found.');
  }
  if (endIndex < startIndex) {
    throw new Error('README markers are in the wrong order.');
  }

  const before = readme.slice(0, startIndex);
  const after = readme.slice(endIndex + END_MARKER.length);
  const section = `${START_MARKER}\n\n${generated.trimEnd()}\n\n${END_MARKER}`;
  return `${before}${section}${after}`;
}

function main() {
  try {
    const config = loadConfig();
    const generated = buildGeneratedContent(config);
    const readme = fs.readFileSync(README_PATH, 'utf8');
    const updated = injectContent(readme, generated);
    fs.writeFileSync(README_PATH, updated, 'utf8');
    console.log('README client sections regenerated successfully.');
  } catch (error) {
    console.error('Failed to generate README content:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
