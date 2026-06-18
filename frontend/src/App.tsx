import { FormEvent, useEffect, useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type Page = 'dashboard' | 'documents' | 'upload' | 'chat' | 'history' | 'users' | 'logs' | 'metrics';

type User = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  team_id: number | null;
  team_name?: string | null;
};

type DocumentItem = {
  id: number;
  title: string;
  filename: string;
  visibility: string;
  team_id: number | null;
  owner_id: number;
  chunk_count: number;
  created_at: string;
};

type Citation = {
  document_id: number;
  document_title: string;
  chunk_id: number;
  chunk_index: number;
  score: number;
  vector_score?: number;
  keyword_score?: number;
  text: string;
};

type ChatResult = {
  session_id: number;
  message_id?: number;
  answer: string;
  citations: Citation[];
  provider: string;
  grounded: boolean;
  latency_ms: number;
  estimated_cost_usd: number;
};

type ChatSession = {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Array<{ id: number; role: string; content: string; citations: Citation[]; latency_ms?: number; created_at: string }>;
};

type Metrics = {
  documents: number;
  chunks: number;
  queries: number;
  average_latency_ms: number;
  estimated_cost_usd: number;
  top_questions: string[];
  failed_answers: number;
};

type LLMRequest = {
  id: number;
  request_id: string;
  provider: string;
  model?: string;
  status: string;
  latency_ms: number;
  total_tokens: number;
  estimated_cost_usd: number;
  error?: string;
  created_at: string;
};

type AuditLog = {
  id: number;
  request_id?: string;
  user_id?: number;
  action: string;
  resource_type?: string;
  resource_id?: string;
  status: string;
  metadata_json?: string;
  latency_ms?: number;
  created_at: string;
};

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

async function readError(response: Response) {
  const body = await response.text();
  try {
    return JSON.parse(body).detail || body;
  } catch {
    return body || response.statusText;
  }
}

export default function App() {
  const [page, setPage] = useState<Page>('dashboard');
  const [token, setToken] = useState(() => localStorage.getItem('rag_token') || '');
  const [user, setUser] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [llmRequests, setLlmRequests] = useState<LLMRequest[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [chatResult, setChatResult] = useState<ChatResult | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);

  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('ChangeMe123!');
  const [fullName, setFullName] = useState('Admin User');
  const [teamName, setTeamName] = useState('HR');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');
  const [visibility, setVisibility] = useState<'private' | 'team' | 'public'>('team');
  const [title, setTitle] = useState('');
  const [teamId, setTeamId] = useState('');
  const [question, setQuestion] = useState('How early should vacation requests be submitted?');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isManager = user?.role === 'admin' || user?.role === 'manager';
  const isAdmin = user?.role === 'admin';

  const localStats = useMemo(() => {
    const chunks = documents.reduce((sum, document) => sum + document.chunk_count, 0);
    return { documents: documents.length, chunks };
  }, [documents]);

  const request = async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
    const response = await fetch(`${API_BASE}${path}`, options);
    if (!response.ok) throw new Error(await readError(response));
    return response.json() as Promise<T>;
  };

  const loadSession = async (nextToken = token) => {
    if (!nextToken) return;
    const me = await request<User>('/api/auth/me', { headers: authHeaders(nextToken) });
    const docs = await request<DocumentItem[]>('/api/documents', { headers: authHeaders(nextToken) });
    const history = await request<ChatSession[]>('/api/chat/history', { headers: authHeaders(nextToken) });
    setUser(me);
    setDocuments(docs);
    setSessions(history);
    if (me.role === 'admin' || me.role === 'manager') {
      setMetrics(await request<Metrics>('/api/admin/metrics', { headers: authHeaders(nextToken) }));
      setLlmRequests(await request<LLMRequest[]>('/api/admin/llm-requests', { headers: authHeaders(nextToken) }));
      setAuditLogs(await request<AuditLog[]>('/api/admin/audit-logs', { headers: authHeaders(nextToken) }));
    }
    if (me.role === 'admin') {
      setUsers(await request<User[]>('/api/auth/users', { headers: authHeaders(nextToken) }));
    }
  };

  useEffect(() => {
    loadSession().catch(() => {
      localStorage.removeItem('rag_token');
      setToken('');
    });
  }, []);

  const submitAuth = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (authMode === 'register') {
        await request<User>('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, full_name: fullName, team_name: teamName || null })
        });
      }
      const result = await request<{ access_token: string }>('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      localStorage.setItem('rag_token', result.access_token);
      setToken(result.access_token);
      await loadSession(result.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const uploadDocument = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      if (title.trim()) form.append('title', title.trim());
      form.append('visibility', visibility);
      if (teamId.trim()) form.append('team_id', teamId.trim());
      await request('/api/documents', { method: 'POST', headers: authHeaders(token), body: form });
      await loadSession(token);
      setTitle('');
      setPage('documents');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const askQuestion = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await request<ChatResult>('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ question, top_k: 5, session_id: activeSessionId })
      });
      setChatResult(result);
      setActiveSessionId(result.session_id);
      await loadSession(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const updateUser = async (id: number, role: string, team_name: string) => {
    await request<User>(`/api/auth/users/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ role, team_name: team_name || null })
    });
    await loadSession(token);
  };

  const logout = () => {
    localStorage.removeItem('rag_token');
    setToken('');
    setUser(null);
    setDocuments([]);
    setSessions([]);
    setChatResult(null);
  };

  if (!user) {
    return (
      <main className="login-page">
        <form className="login-panel" onSubmit={submitAuth}>
          <p className="eyebrow">Enterprise RAG</p>
          <h1>{authMode === 'register' ? 'Create account' : 'Login'}</h1>
          <div className="tabs">
            <button type="button" className={authMode === 'register' ? 'active' : ''} onClick={() => setAuthMode('register')}>Register</button>
            <button type="button" className={authMode === 'login' ? 'active' : ''} onClick={() => setAuthMode('login')}>Login</button>
          </div>
          <label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          {authMode === 'register' && (
            <>
              <label>Full name<input value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
              <label>Team<input value={teamName} onChange={(event) => setTeamName(event.target.value)} /></label>
            </>
          )}
          <button className="primary" disabled={busy}>{busy ? 'Working...' : 'Continue'}</button>
          {error && <p className="error">{error}</p>}
        </form>
      </main>
    );
  }

  const nav: Array<[Page, string]> = [
    ['dashboard', 'Dashboard'],
    ['documents', 'Documents'],
    ['upload', 'Upload document'],
    ['chat', 'Chat'],
    ['history', 'Chat history'],
    ['users', 'Users'],
    ['logs', 'Logs'],
    ['metrics', 'Metrics']
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Enterprise RAG</p>
          <h1>Admin Console</h1>
        </div>
        <nav>
          {nav.map(([key, label]) => {
            if ((key === 'users' && !isAdmin) || ((key === 'logs' || key === 'metrics') && !isManager)) return null;
            return <button key={key} className={page === key ? 'active' : ''} onClick={() => setPage(key)}>{label}</button>;
          })}
        </nav>
        <div className="identity">
          <strong>{user.full_name}</strong>
          <span>{user.role} {user.team_name ? `/ ${user.team_name}` : ''}</span>
          <span>{user.email}</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </aside>

      <main className="workspace">
        {page === 'dashboard' && (
          <>
            <Header title="Dashboard" subtitle="Operational health, usage, and failed answer signals." />
            <MetricGrid metrics={metrics} localStats={localStats} />
            <section className="panel">
              <h3>Top questions</h3>
              <List items={metrics?.top_questions || []} empty="No questions yet." />
            </section>
          </>
        )}

        {page === 'documents' && (
          <>
            <Header title="Documents" subtitle="Documents visible under the current user's RBAC scope." />
            <DocumentTable documents={documents} />
          </>
        )}

        {page === 'upload' && (
          <>
            <Header title="Upload document" subtitle="PDF, DOCX, and TXT ingestion with private/team/public visibility." />
            <section className="panel form-panel">
              <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="HR Handbook" /></label>
              <div className="field-row">
                <label>Visibility<select value={visibility} onChange={(event) => setVisibility(event.target.value as typeof visibility)}>
                  <option value="private">Private</option>
                  <option value="team">Team</option>
                  <option value="public">Public</option>
                </select></label>
                <label>Team ID<input value={teamId} onChange={(event) => setTeamId(event.target.value)} placeholder={user.team_id ? String(user.team_id) : 'optional'} /></label>
              </div>
              <label className="dropzone">
                <input type="file" accept=".pdf,.docx,.txt" disabled={busy} onChange={(event) => event.target.files?.[0] && uploadDocument(event.target.files[0])} />
                <span>{busy ? 'Processing...' : 'Select document'}</span>
              </label>
            </section>
          </>
        )}

        {page === 'chat' && (
          <>
            <Header title="Chat" subtitle="Grounded answers only. If documents do not support the answer, the assistant falls back." />
            <form className="panel chat-panel" onSubmit={askQuestion}>
              <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
              <button className="primary" disabled={busy || !question.trim()}>{busy ? 'Asking...' : 'Ask'}</button>
            </form>
            {chatResult && <AnswerPanel result={chatResult} />}
          </>
        )}

        {page === 'history' && (
          <>
            <Header title="Chat history" subtitle="Conversation memory and previous grounded answers." />
            <div className="stack">{sessions.map((session) => <SessionCard key={session.id} session={session} onContinue={() => { setActiveSessionId(session.id); setPage('chat'); }} />)}</div>
          </>
        )}

        {page === 'users' && isAdmin && (
          <>
            <Header title="Users" subtitle="Admin role and team assignment." />
            <UsersTable users={users} onUpdate={updateUser} />
          </>
        )}

        {page === 'logs' && isManager && (
          <>
            <Header title="Logs" subtitle="Audit log and LLM request status." />
            <LogsTable auditLogs={auditLogs} llmRequests={llmRequests} />
          </>
        )}

        {page === 'metrics' && isManager && (
          <>
            <Header title="Metrics" subtitle="Latency, cost, tokens, success/fail status." />
            <MetricGrid metrics={metrics} localStats={localStats} />
            <LLMTable rows={llmRequests} />
          </>
        )}
      </main>

      {error && <div className="toast">{error}</div>}
    </div>
  );
}

function Header({ title, subtitle }: { title: string; subtitle: string }) {
  return <section className="topbar"><div><h2>{title}</h2><p>{subtitle}</p></div></section>;
}

function MetricGrid({ metrics, localStats }: { metrics: Metrics | null; localStats: { documents: number; chunks: number } }) {
  const data = [
    ['Documents', metrics?.documents ?? localStats.documents],
    ['Chunks', metrics?.chunks ?? localStats.chunks],
    ['Queries', metrics?.queries ?? 0],
    ['Avg latency', `${Math.round(metrics?.average_latency_ms || 0)}ms`],
    ['Cost', `$${(metrics?.estimated_cost_usd || 0).toFixed(4)}`],
    ['Failed answers', metrics?.failed_answers ?? 0]
  ];
  return <section className="metric-grid">{data.map(([label, value]) => <div className="metric-card" key={label}><span>{label}</span><strong>{value}</strong></div>)}</section>;
}

function DocumentTable({ documents }: { documents: DocumentItem[] }) {
  return <section className="panel table">{documents.map((doc) => <article className="row" key={doc.id}><strong>{doc.title}</strong><span>{doc.filename}</span><span>{doc.visibility}</span><span>{doc.chunk_count} chunks</span><span>team {doc.team_id || '-'}</span></article>)}</section>;
}

function AnswerPanel({ result }: { result: ChatResult }) {
  return <section className="panel answer"><span className={result.grounded ? 'status pass' : 'status fail'}>{result.grounded ? 'grounded' : 'fallback'}</span><span>{result.provider}</span><span>{result.latency_ms}ms</span><p>{result.answer}</p><div className="stack">{result.citations.map((citation, index) => <article className="citation" key={citation.chunk_id}><strong>[{index + 1}] {citation.document_title}</strong><span>score {citation.score.toFixed(3)} / vector {(citation.vector_score || 0).toFixed(3)} / keyword {(citation.keyword_score || 0).toFixed(3)}</span><p>{citation.text}</p></article>)}</div></section>;
}

function SessionCard({ session, onContinue }: { session: ChatSession; onContinue: () => void }) {
  return <section className="panel"><div className="split"><h3>{session.title}</h3><button onClick={onContinue}>Continue</button></div>{session.messages.map((message) => <article className="message" key={message.id}><strong>{message.role}</strong><p>{message.content}</p></article>)}</section>;
}

function UsersTable({ users, onUpdate }: { users: User[]; onUpdate: (id: number, role: string, team: string) => Promise<void> }) {
  return <section className="panel table">{users.map((user) => <UserRow key={user.id} user={user} onUpdate={onUpdate} />)}</section>;
}

function UserRow({ user, onUpdate }: { user: User; onUpdate: (id: number, role: string, team: string) => Promise<void> }) {
  const [role, setRole] = useState(user.role);
  const [team, setTeam] = useState(user.team_name || '');
  return <article className="row"><strong>{user.email}</strong><span>{user.full_name}</span><select value={role} onChange={(event) => setRole(event.target.value)}><option>admin</option><option>manager</option><option>employee</option></select><input value={team} onChange={(event) => setTeam(event.target.value)} /><button onClick={() => onUpdate(user.id, role, team)}>Save</button></article>;
}

function LogsTable({ auditLogs, llmRequests }: { auditLogs: AuditLog[]; llmRequests: LLMRequest[] }) {
  return <div className="two-col"><section className="panel table"><h3>Audit logs</h3>{auditLogs.map((log) => <article className="row" key={log.id}><strong>{log.action}</strong><span>{log.status}</span><span>{log.resource_type || '-'}</span><span>{log.created_at}</span></article>)}</section><LLMTable rows={llmRequests} /></div>;
}

function LLMTable({ rows }: { rows: LLMRequest[] }) {
  return <section className="panel table"><h3>LLM requests</h3>{rows.map((row) => <article className="row" key={row.id}><strong>{row.status}</strong><span>{row.provider}</span><span>{row.total_tokens} tokens</span><span>{row.latency_ms}ms</span><span>${row.estimated_cost_usd.toFixed(4)}</span></article>)}</section>;
}

function List({ items, empty }: { items: string[]; empty: string }) {
  return <div className="stack">{items.length ? items.map((item) => <p className="list-item" key={item}>{item}</p>) : <p className="empty">{empty}</p>}</div>;
}
