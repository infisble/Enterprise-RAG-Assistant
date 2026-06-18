import { FormEvent, useEffect, useMemo, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
  text: string;
};

type ChatResult = {
  answer: string;
  citations: Citation[];
  provider: string;
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
  const [token, setToken] = useState(() => localStorage.getItem('rag_token') || '');
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('ChangeMe123!');
  const [fullName, setFullName] = useState('Admin User');
  const [teamName, setTeamName] = useState('HR');
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');
  const [visibility, setVisibility] = useState<'private' | 'team' | 'public'>('team');
  const [title, setTitle] = useState('');
  const [teamId, setTeamId] = useState('');
  const [question, setQuestion] = useState('What does the policy say?');
  const [chatResult, setChatResult] = useState<ChatResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stats = useMemo(() => {
    const chunks = documents.reduce((sum, document) => sum + document.chunk_count, 0);
    const publicCount = documents.filter((document) => document.visibility === 'public').length;
    return { documents: documents.length, chunks, publicCount };
  }, [documents]);

  const request = async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
    const response = await fetch(`${API_BASE}${path}`, options);
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    return response.json() as Promise<T>;
  };

  const loadSession = async (nextToken = token) => {
    if (!nextToken) return;
    const me = await request<User>('/api/auth/me', { headers: authHeaders(nextToken) });
    const docs = await request<DocumentItem[]>('/api/documents', { headers: authHeaders(nextToken) });
    setUser(me);
    setDocuments(docs);
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
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      if (title.trim()) form.append('title', title.trim());
      form.append('visibility', visibility);
      if (teamId.trim()) form.append('team_id', teamId.trim());
      await request('/api/documents', {
        method: 'POST',
        headers: authHeaders(token),
        body: form
      });
      await loadSession(token);
      setTitle('');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const askQuestion = async (event: FormEvent) => {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const result = await request<ChatResult>('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ question, top_k: 5 })
      });
      setChatResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('rag_token');
    setToken('');
    setUser(null);
    setDocuments([]);
    setChatResult(null);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Enterprise RAG</p>
          <h1>Assistant Console</h1>
        </div>
        {user ? (
          <div className="identity">
            <strong>{user.full_name}</strong>
            <span>{user.email}</span>
            <span>{user.role} {user.team_name ? `/${user.team_name}` : ''}</span>
            <button onClick={logout}>Sign out</button>
          </div>
        ) : (
          <form className="auth-form" onSubmit={submitAuth}>
            <div className="tabs">
              <button type="button" className={authMode === 'register' ? 'active' : ''} onClick={() => setAuthMode('register')}>
                Register
              </button>
              <button type="button" className={authMode === 'login' ? 'active' : ''} onClick={() => setAuthMode('login')}>
                Login
              </button>
            </div>
            <label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {authMode === 'register' && (
              <>
                <label>Full name<input value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
                <label>Team<input value={teamName} onChange={(event) => setTeamName(event.target.value)} /></label>
              </>
            )}
            <button className="primary" disabled={busy}>{busy ? 'Working...' : authMode === 'register' ? 'Create account' : 'Sign in'}</button>
          </form>
        )}
      </aside>

      <main className="workspace">
        <section className="topbar">
          <div>
            <h2>Knowledge Base</h2>
            <p>Upload private, team, or public documents and ask questions with citations.</p>
          </div>
          <div className="stats">
            <span><strong>{stats.documents}</strong> docs</span>
            <span><strong>{stats.chunks}</strong> chunks</span>
            <span><strong>{stats.publicCount}</strong> public</span>
          </div>
        </section>

        <section className="content-grid">
          <div className="panel">
            <h3>Upload</h3>
            <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Quarterly HR policy" /></label>
            <div className="field-row">
              <label>Visibility
                <select value={visibility} onChange={(event) => setVisibility(event.target.value as typeof visibility)}>
                  <option value="private">Private</option>
                  <option value="team">Team</option>
                  <option value="public">Public</option>
                </select>
              </label>
              <label>Team ID<input value={teamId} onChange={(event) => setTeamId(event.target.value)} placeholder={user?.team_id ? String(user.team_id) : 'optional'} /></label>
            </div>
            <label className="dropzone">
              <input type="file" accept=".pdf,.docx,.txt" disabled={!user || busy} onChange={(event) => event.target.files?.[0] && uploadDocument(event.target.files[0])} />
              <span>{busy ? 'Processing...' : 'Select PDF, DOCX, or TXT'}</span>
            </label>
          </div>

          <form className="panel chat-panel" onSubmit={askQuestion}>
            <h3>Chat</h3>
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
            <button className="primary" disabled={!user || busy || !question.trim()}>Ask</button>
            {chatResult && (
              <div className="answer">
                <span className="provider">Provider: {chatResult.provider}</span>
                <p>{chatResult.answer}</p>
              </div>
            )}
          </form>

          <div className="panel documents-panel">
            <h3>Accessible Documents</h3>
            <div className="document-list">
              {documents.map((document) => (
                <article key={document.id} className="document-row">
                  <div>
                    <strong>{document.title}</strong>
                    <span>{document.filename}</span>
                  </div>
                  <div className="badges">
                    <span>{document.visibility}</span>
                    <span>{document.chunk_count} chunks</span>
                  </div>
                </article>
              ))}
              {!documents.length && <p className="empty">No accessible documents yet.</p>}
            </div>
          </div>

          <div className="panel citations-panel">
            <h3>Sources</h3>
            <div className="citation-list">
              {chatResult?.citations.map((citation, index) => (
                <article key={citation.chunk_id} className="citation">
                  <strong>[{index + 1}] {citation.document_title}</strong>
                  <span>chunk {citation.chunk_index} / score {citation.score.toFixed(3)}</span>
                  <p>{citation.text}</p>
                </article>
              ))}
              {!chatResult?.citations.length && <p className="empty">Citations appear after a chat response.</p>}
            </div>
          </div>
        </section>
      </main>

      {error && <div className="toast">{error}</div>}
    </div>
  );
}
