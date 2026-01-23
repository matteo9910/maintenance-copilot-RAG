import { ModelOption, Reference, ChatSession } from './types';

export const AI_MODELS: ModelOption[] = [
  { id: 'anthropic/claude-sonnet-4', name: 'Sonnet 4.5', provider: 'Anthropic', description: 'Reasoning', available: true },
  { id: 'openai/gpt-4o', name: 'GPT-4o', provider: 'OpenAI', description: 'General Purpose', available: true },
  { id: 'openai/gpt-5', name: 'GPT-5', provider: 'OpenAI', description: 'Latest', available: true },
  { id: 'google/gemini-3-pro-preview', name: 'Gemini 3 Pro Preview', provider: 'Google', description: 'Multimodal', available: true },
];

export const MOCK_HISTORY: ChatSession[] = [];

export const SUGGESTIONS: { title: string; subtitle: string; icon: string }[] = [];

// Mock technical schematic for the demo scenario
export const VALVE_SCHEMATIC_REF: Reference = {
  id: 'ref-valve-01',
  title: 'Pneumatic Control Valve Series V-200',
  source: 'Siemens Maintenance Manual',
  page: 'Pg. 45, Section 3.2',
  imageUrl: 'https://picsum.photos/id/400/800/600',
  description: 'Exploded view of the primary diaphragm assembly and actuator coupling.'
};
