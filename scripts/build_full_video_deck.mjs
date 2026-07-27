import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import PptxGenJS from "pptxgenjs";

const project = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const cardsDir = process.env.CARDS_DIR || path.join(project, "data/cards/full_video_final");
const clipsManifest = process.env.CLIPS_MANIFEST || path.join(project, "data/clips/semantic_all/manifest.json");
const output = process.env.OUTPUT_PPTX || path.join(project, "outputs/Radiology_Report_Teaching_Atlas_Full_Video_zh-TW.pptx");
const deckDate = process.env.DECK_DATE || "2026-07-16";
const cards = fs.readdirSync(cardsDir)
  .filter((name) => /^CARD\d{3}\.json$/.test(name))
  .sort()
  .map((name) => JSON.parse(fs.readFileSync(path.join(cardsDir, name), "utf8")));
const semanticManifest = Object.fromEntries(
  JSON.parse(fs.readFileSync(clipsManifest, "utf8"))
    .map((item) => [item.card_id, item]),
);

const defaultSections = [
  { title: "報告與基礎判讀", subtitle: "Enhancement、bone window、比較與標準術語", ids: cards.slice(0, 7).map((c) => c.card_id) },
  { title: "術後、出血與 stroke", subtitle: "術後變化、mass effect、infarct age 與取栓後判讀", ids: cards.slice(7, 15).map((c) => c.card_id) },
  { title: "Head & neck 與 oncology", subtitle: "腫瘤來源、淋巴結與軟組織病灶", ids: cards.slice(15, 18).map((c) => c.card_id) },
  { title: "Spine 與神經鑑別", subtitle: "Blood、leptomeningeal disease、PRES 與 ODS", ids: cards.slice(18, 22).map((c) => c.card_id) },
  { title: "腫瘤與 treatment effect", subtitle: "Glioma、術後 baseline、radiation change 與 protocol", ids: cards.slice(22, 29).map((c) => c.card_id) },
  { title: "感染、出血與安全溝通", subtitle: "ICH workup、vascular cause 與避免不必要處置", ids: cards.slice(29, 34).map((c) => c.card_id) },
];
const datedSections = cards.length === 26 ? [
  { title: "基礎判讀與初始線索", subtitle: "Sella、硬腦膜出血與灌流影像", ids: cards.slice(0, 3).map((c) => c.card_id) },
  { title: "Moyamoya 與 EDAS", subtitle: "Flow void、ivy sign、collateral、perfusion 與術後追蹤", ids: cards.slice(3, 10).map((c) => c.card_id) },
  { title: "PSP 與量化影像", subtitle: "MRPI、MRPI 2.0 與臨床適用限制", ids: cards.slice(10, 13).map((c) => c.card_id) },
  { title: "腫瘤分期與腦中風", subtitle: "DOI、慢性病灶、M1 occlusion 與 EVT", ids: cards.slice(13, 17).map((c) => c.card_id) },
  { title: "Sellar、spine 與 glioma", subtitle: "Macroadenoma、craniopharyngioma、dural ectasia 與治療後變化", ids: cards.slice(17, 23).map((c) => c.card_id) },
  { title: "NPC 與顱底神經", subtitle: "Location-first differential、壞死與 hypoglossal palsy", ids: cards.slice(23).map((c) => c.card_id) },
] : [
  { title: "急診與腦血管", subtitle: "Delirium、stroke、灌流與硬腦膜下出血", ids: cards.slice(0, 5).map((c) => c.card_id) },
  { title: "淋巴瘤與腫瘤追蹤", subtitle: "跨模態判讀、治療反應與量測原則", ids: cards.slice(5, 9).map((c) => c.card_id) },
  { title: "癲癇與失智影像", subtitle: "PRES、MTA、核醫與定量分析", ids: cards.slice(9, 13).map((c) => c.card_id) },
  { title: "轉移與出血性病灶", subtitle: "Metastasis、病理性骨折與治療後變化", ids: cards.slice(13, 18).map((c) => c.card_id) },
  { title: "顱底與周邊神經", subtitle: "Perineural spread、海綿竇旁病灶與去神經變化", ids: cards.slice(18).map((c) => c.card_id) },
];
const sections = cards.length === 34 ? defaultSections : datedSections;

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Radiology Report Teaching Atlas";
pptx.subject = "34 teaching cards with embedded videos";
pptx.title = "Radiology Report Teaching Atlas - Full Video Edition";
pptx.company = "Radiology Report Teaching Atlas";
pptx.lang = "zh-TW";
pptx.theme = { headFontFace: "PingFang TC", bodyFontFace: "PingFang TC", lang: "zh-TW" };

const C = { ink: "111111", blue: "168BDF", pale: "EAF5FB", rule: "C7CDD4", muted: "5B6470", panel: "F4F6F8" };

function addText(slide, text, x, y, w, h, options = {}) {
  slide.addText(String(text || "needs human completion"), {
    x, y, w, h, fontFace: "PingFang TC", fontSize: options.fontSize ?? 18,
    color: options.color ?? C.ink, bold: options.bold ?? false, margin: options.margin ?? 0,
    valign: options.valign ?? "top", fit: "shrink", breakLine: false, ...options,
  });
}

function footer(slide, page) {
  addText(slide, "Radiology Report Teaching Atlas · AI-assisted draft · teacher review required", 0.45, 7.13, 8.4, 0.16, { fontSize: 7.5, color: C.muted });
  addText(slide, String(page), 12.45, 7.13, 0.35, 0.16, { fontSize: 8, color: C.muted, align: "right" });
}

function heading(slide, eyebrow, title, page) {
  addText(slide, eyebrow, 0.45, 0.25, 7.5, 0.24, { fontSize: 10, color: C.blue, bold: true });
  addText(slide, title, 0.45, 0.62, 12.35, 0.6, { fontSize: 25, bold: true });
  slide.addShape(pptx.ShapeType.line, { x: 0.45, y: 1.34, w: 12.4, h: 0, line: { color: C.rule, width: 1 } });
  footer(slide, page);
}

function labelBlock(slide, label, text, x, y, w, h, fontSize = 16) {
  addText(slide, label, x, y, w, 0.24, { fontSize: 13, color: C.blue, bold: true });
  addText(slide, text, x, y + 0.31, w, h - 0.31, { fontSize });
}

function dataUri(file) {
  const ext = path.extname(file).slice(1).toLowerCase();
  const mime = ext === "png" ? "image/png" : "image/jpeg";
  return `data:${mime};base64,${fs.readFileSync(file).toString("base64")}`;
}

function containMediaRect(file, frame) {
  const raw = execFileSync("ffprobe", [
    "-v", "error", "-select_streams", "v:0",
    "-show_entries", "stream=width,height", "-of", "csv=p=0", file,
  ], { encoding: "utf8" }).trim();
  const [width, height] = raw.split(",").map(Number);
  if (!width || !height) throw new Error(`Cannot read video dimensions: ${file}`);
  const scale = Math.min(frame.w / width, frame.h / height);
  const w = width * scale;
  const h = height * scale;
  return { x: frame.x + (frame.w - w) / 2, y: frame.y + (frame.h - h) / 2, w, h };
}

let page = 0;
{
  const slide = pptx.addSlide(); page += 1;
  slide.background = { color: "FFFFFF" };
  slide.addShape(pptx.ShapeType.line, { x: 0.55, y: 1.35, w: 0, h: 3.9, line: { color: "42B7F5", width: 3 } });
  addText(slide, `Full Video Teaching Atlas · ${deckDate}`, 0.55, 0.38, 6, 0.28, { fontSize: 11, color: C.blue, bold: true });
  addText(slide, "Radiology Report\nTeaching Atlas", 0.78, 1.68, 7.4, 1.28, { fontSize: 34, bold: true, breakLine: true });
  addText(slide, `${cards.length} 張教學卡 · ${Object.keys(semanticManifest).length} 段完整語意教學影片`, 0.78, 3.25, 8.2, 0.4, { fontSize: 20 });
  addText(slide, "投影片模式下按一下影像即可播放", 0.78, 3.92, 6.5, 0.3, { fontSize: 15, color: C.muted });
  footer(slide, page);
}

{
  const slide = pptx.addSlide(); page += 1;
  heading(slide, "HOW TO USE", "每張教學卡如何閱讀", page);
  labelBlock(slide, "教學重點", "由完整逐字稿整理可重複使用的判讀原則。", 0.7, 1.9, 5.5, 1.2, 21);
  labelBlock(slide, "常見陷阱", "指出容易造成誤判、漏報或不必要處置的思考捷徑。", 6.8, 1.9, 5.5, 1.2, 21);
  labelBlock(slide, "影片與靜態圖", "高影像依賴卡片使用完整語意 teaching clip；文字型卡片保留靜態影像或完整文字。", 0.7, 3.65, 5.5, 1.45, 21);
  labelBlock(slide, "教師確認", "所有素材維持 needs_review；確認序列、切面與教學切點後再用於正式課程。", 6.8, 3.65, 5.5, 1.45, 21);
}

{
  const slide = pptx.addSlide(); page += 1;
  heading(slide, "PROJECT SNAPSHOT", `${cards.length} 張 Cards 橫跨 ${sections.length} 個教學主題`, page);
  const totalSeconds = Object.values(semanticManifest).reduce((sum, item) => sum + item.duration_seconds, 0);
  const totalTime = `${Math.floor(totalSeconds / 60)}:${String(Math.round(totalSeconds % 60)).padStart(2, "0")}`;
  const stats = [[String(cards.length), "完整教學事件"], [String(Object.keys(semanticManifest).length), "內嵌短影片"], [String(sections.length), "教學主題"], [totalTime, "語意影片總長"]];
  stats.forEach(([value, label], i) => {
    const x = 0.6 + i * 3.12;
    slide.addShape(pptx.ShapeType.rect, { x, y: 2.05, w: 2.62, h: 1.45, fill: { color: C.panel }, line: { color: "E1E5E9", width: 1 } });
    addText(slide, value, x + 0.18, 2.28, 2.15, 0.52, { fontSize: 28, bold: true, color: i === 1 ? C.blue : C.ink });
    addText(slide, label, x + 0.18, 3.02, 2.15, 0.24, { fontSize: 12, color: C.muted });
  });
  addText(slide, "影片是影像證據，不取代教師對序列、病灶與診斷推理的確認。", 0.6, 4.35, 11.9, 0.5, { fontSize: 20, bold: true });
}

for (const [sectionIndex, section] of sections.entries()) {
  {
    const slide = pptx.addSlide(); page += 1;
    slide.background = { color: "FFFFFF" };
    addText(slide, `SECTION ${String(sectionIndex + 1).padStart(2, "0")}`, 0.65, 0.55, 3.5, 0.26, { fontSize: 11, color: C.blue, bold: true });
    addText(slide, section.title, 0.65, 2.28, 6.4, 0.95, { fontSize: 34, bold: true });
    addText(slide, section.subtitle, 0.65, 3.43, 6.2, 0.55, { fontSize: 17, color: C.muted });
    section.ids.forEach((id, i) => {
      const card = cards.find((item) => item.card_id === id);
      addText(slide, `${String(i + 1).padStart(2, "0")}  ${card.topic}`, 7.55, 1.65 + i * 0.55, 4.85, 0.36, { fontSize: 12, bold: i === 0 });
    });
    footer(slide, page);
  }

  for (const id of section.ids) {
    const card = cards.find((item) => item.card_id === id);
    const slide = pptx.addSlide(); page += 1;
    slide.background = { color: "FFFFFF" };
    const evidence = card.optional_image_evidence || {};
      const semanticInfo = semanticManifest[id];
      const semanticClip = semanticInfo ? path.join(project, semanticInfo.teaching_clip) : "";
      const clip = semanticClip || (evidence.scroll_clip ? path.join(project, evidence.scroll_clip) : "");
    const screenshot = evidence.key_screenshot ? path.join(project, evidence.key_screenshot) : "";
    const mediaExists = clip && fs.existsSync(clip);
    const imageExists = screenshot && fs.existsSync(screenshot);
    heading(slide, `${card.card_id} · ${card.timestamp_range} · ${mediaExists ? "內嵌影片" : "教學卡"}`, card.topic, page);

    if (mediaExists || imageExists) {
      labelBlock(slide, "教學重點", card.key_teaching_point, 0.45, 1.72, 4.85, 1.68, 17);
      labelBlock(slide, "常見陷阱", card.common_pitfall, 0.45, 3.62, 4.85, 1.15, 16);
      labelBlock(slide, "下次報告注意", card.checklist_item_for_next_report, 0.45, 4.98, 4.85, 1.25, 15);
      const mediaFrame = { x: 5.55, y: 1.72, w: 7.28, h: 4.08 };
      if (mediaExists) {
        const mediaRect = containMediaRect(clip, mediaFrame);
        slide.addShape(pptx.ShapeType.rect, { ...mediaRect, fill: { color: "000000" }, line: { color: C.rule, width: 1 } });
        slide.addMedia({ type: "video", path: clip, cover: imageExists ? dataUri(screenshot) : undefined, ...mediaRect, objectName: `${id} scroll clip` });
        const clipDuration = semanticInfo ? `${Math.round(semanticInfo.duration_seconds)} 秒` : "12 秒";
        addText(slide, `按一下影像播放完整教學片段 · ${clipDuration}`, 5.7, 5.86, 4.6, 0.22, { fontSize: 10, color: C.muted });
      } else {
        slide.addShape(pptx.ShapeType.rect, { ...mediaFrame, fill: { color: C.pale }, line: { color: C.rule, width: 1 } });
        slide.addImage({ path: screenshot, ...mediaFrame, sizing: "contain" });
      }
      slide.addShape(pptx.ShapeType.rect, { x: 5.55, y: 6.12, w: 7.28, h: 0.72, fill: { color: C.panel }, line: { color: C.rule, width: 1 } });
      addText(slide, "建議報告句", 5.75, 6.25, 1.15, 0.2, { fontSize: 11, color: C.blue, bold: true });
      addText(slide, card.improved_report_phrase, 6.95, 6.21, 5.62, 0.45, { fontSize: 10.5 });
    } else {
      labelBlock(slide, "教學重點", card.key_teaching_point, 0.7, 1.85, 5.45, 1.55, 20);
      labelBlock(slide, "常見陷阱", card.common_pitfall, 0.7, 3.85, 5.45, 1.3, 18);
      labelBlock(slide, "建議報告句", card.improved_report_phrase, 6.75, 1.85, 5.55, 1.75, 17);
      labelBlock(slide, "下次報告注意", card.checklist_item_for_next_report, 6.75, 4.05, 5.55, 1.25, 18);
    }
  }
}

await pptx.writeFile({ fileName: output });
console.log(JSON.stringify({ output, slides: pptx._slides.length, embeddedVideos: Object.keys(semanticManifest).length }, null, 2));
