#!/usr/bin/env tsx
import fs from 'node:fs';
import path from 'node:path';

function argValue(name: string): string | undefined {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

async function main() {
  const output = argValue('--output');
  const character = argValue('--character') ?? 'unknown';
  const wikiName = argValue('--wiki-name') ?? 'unknown';
  const dryRun = process.argv.includes('--dry-run');
  if (!output) {
    console.error('缺少 --output');
    process.exit(2);
  }
  fs.mkdirSync(path.dirname(output), { recursive: true });
  if (dryRun) {
    fs.writeFileSync(output, JSON.stringify({
      status: 'success',
      source_name: 'FandomScraper dry-run',
      source_url: `https://${wikiName}.fandom.com/wiki/${encodeURIComponent(character)}`,
      title: character,
      sections: {
        appearance: `${character} 的外观资料示例。`,
        personality: `${character} 的性格、身份和心理状态资料示例。`,
        relationships: `${character} 的人物关系资料示例。`,
        story: `${character} 的剧情经历资料示例。`
      }
    }, null, 2), 'utf8');
    return;
  }
  const { FandomScraper } = await import('fandom-scraper');
  const scraper = new FandomScraper(wikiName);
  const charactersPage = argValue('--characters-page-url');
  if (charactersPage) scraper.setCharactersPage(charactersPage);
  let result;
  try {
    result = await scraper.findByName(character).exec();
  } catch {
    const all = await scraper.findAll().exec();
    result = all.find((item: any) => String(item?.name ?? '').toLowerCase().includes(character.toLowerCase()));
  }
  fs.writeFileSync(output, JSON.stringify({ status: 'success', source_name: 'FandomScraper', source_url: '', title: character, data: result }, null, 2), 'utf8');
}

main().catch(error => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
