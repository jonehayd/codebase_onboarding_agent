import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, spyOn } from 'storybook/test';
import IngestionPage from './IngestionPage';

const MOCK_SESSION = {
  session_id: 1,
  title: 'discord_bot',
  repo: { owner: 'jonehayd', name: 'discord_bot' },
};

function makeStatus(overrides = {}) {
  return {
    session_id: 1,
    repo_id: 10,
    status: 'processing',
    stage: 'parsing_code',
    percent: 0,
    files_total: 42,
    file_count: 0,
    vector_count: 0,
    elapsed_seconds: 8,
    commit_hash: 'abc1234',
    ...overrides,
  };
}

function mockFetch(statusData) {
  spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
    const u = String(url);
    if (u.includes('/status')) {
      if (statusData === null) throw new Error('Failed to fetch');
      return { ok: true, json: async () => statusData };
    }
    if (u.includes('/cancel') || u.includes('/reingest')) {
      return { ok: true, json: async () => ({ detail: 'ok' }) };
    }
    return { ok: true, json: async () => MOCK_SESSION };
  });
}

function WithRouter({ children }) {
  return (
    <MemoryRouter initialEntries={['/sessions/1']}>
      <Routes>
        <Route path='/sessions/:sessionId' element={children} />
      </Routes>
    </MemoryRouter>
  );
}

export default {
  title: 'Pages/IngestionPage',
  decorators: [
    (Story) => (
      <WithRouter>
        <Story />
      </WithRouter>
    ),
  ],
};

export const Fetching = {
  beforeEach() {
    mockFetch(makeStatus({ status: 'pending', stage: 'fetching_files', percent: 0 }));
  },
  render: () => <IngestionPage />,
};

export const Parsing = {
  beforeEach() {
    mockFetch(makeStatus({ stage: 'parsing_code', percent: 25, file_count: 10 }));
  },
  render: () => <IngestionPage />,
};

export const GeneratingEmbeddings = {
  beforeEach() {
    mockFetch(makeStatus({ stage: 'generating_embeddings', percent: 65, file_count: 42, vector_count: 310, elapsed_seconds: 34 }));
  },
  render: () => <IngestionPage />,
};

export const Completed = {
  beforeEach() {
    mockFetch(makeStatus({ status: 'completed', stage: 'completed', percent: 100, file_count: 42, vector_count: 1204, elapsed_seconds: 61 }));
  },
  render: () => <IngestionPage />,
};

export const Failed = {
  beforeEach() {
    mockFetch(makeStatus({ status: 'failed', stage: 'failed', percent: 0, file_count: 5, vector_count: 0, elapsed_seconds: 12 }));
  },
  render: () => <IngestionPage />,
};

export const Cancelled = {
  beforeEach() {
    mockFetch(makeStatus({ status: 'failed', stage: 'cancelled', percent: 0, file_count: 8, vector_count: 120, elapsed_seconds: 20 }));
  },
  render: () => <IngestionPage />,
};

export const NetworkError = {
  beforeEach() {
    mockFetch(null);
  },
  render: () => <IngestionPage />,
};
