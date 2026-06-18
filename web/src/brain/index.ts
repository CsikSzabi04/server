// Public entry point for the BRAIN engine (AI-1 / MIND).
// AI-2 (3D view) and AI-3 (integration) import everything they need from here.
//   import { useBrainGraph, useBrainLearning } from '../brain';
//   import type { BrainGraph, BrainStats, BrainState } from '../brain';
export * from './contracts';
export { useBrainGraph } from './useBrainGraph';
export { useBrainLearning } from './useBrainLearning';
export { buildBrainGraph } from './graph';
export { decideRoute, arbiterContext, isLocalBrainReady, type ArbiterContext } from './arbiter';
export { BrainLearner, deriveStage, tokenize } from './learn';
export { detectLang, type Lang } from './lang';
export { pickFacts, composeLocalAnswer, answerOffline } from './answer';
export { seedBaseBrain, seedProgramming, seedBrain, SEED_VERSION } from './seedCorpus';
export { SOURCES, TECHS, TECH_LABEL, findSource, type SourceLink, type Tech } from './seed/sources';
export { PROGRAMMING_SNIPPETS, PROGRAMMING_QA, findSnippet, PROG_KEYWORDS, type ProgSnippet, type ProgQA } from './seed/programmingCurated';
export { PROGRAMMING_CHUNKS, PROGRAMMING_SOURCES, PROGRAMMING_SEED_VERSION, type ProgChunk, type ProgSource } from './seed/programming.gen';
export { WEB_RECIPES, findRecipe, renderRecipe, type WebRecipe, type RecipeFile } from './seed/recipes';
export { KNOWLEDGE, findKnowledge, KNOWLEDGE_TEXT, type KnowledgeEntry } from './seed/knowledge';
export { ingestWeb, brainCovers } from './web';
export { loadWebDocs, getWebDocs, webDocCount, topCoveringWebDoc, addWebDoc } from './webStore';
export { trainStage6, stage6Status, predictNextStage6 } from './stage6/net';
export { buildBrainContext } from './grounding';
export { distillFromModel, distilledCount } from './distill';
export { nextStudyTopic, studyQuestion } from './selfStudy';
