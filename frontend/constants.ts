import { ModelOption, Reference, ChatSession } from './types';

export const AI_MODELS: ModelOption[] = [
  { id: 'gpt-5.2', name: 'GPT-5.2', provider: 'Azure OpenAI', description: 'Latest', available: true },
  { id: 'gpt-4.1', name: 'GPT-4.1', provider: 'Azure OpenAI', description: 'Fast & Efficient', available: true },
  { id: 'gpt-5', name: 'GPT-5', provider: 'Azure OpenAI', description: 'Advanced', available: true },
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
