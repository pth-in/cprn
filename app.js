const { useState, useEffect, useCallback, useRef } = React;

const SUPABASE_URL = "https://tvbmjectzcowsjzidumq.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_NFMG2axuLqnH2AbPUjR7OA_L70ojzSM";

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const App = () => {
    const [incidents, setIncidents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedIncident, setSelectedIncident] = useState(null);
    const [initialSync, setInitialSync] = useState(false);
    const [theme, setTheme] = useState(localStorage.getItem('cprn-theme') || 'light');

    // --- Admin State ---
    const [isLoggedIn, setIsLoggedIn] = useState(localStorage.getItem('cprn-logged-in') === 'true');
    const [adminView, setAdminView] = useState('none'); // 'none', 'sources', 'incidents', 'users'
    const [loginError, setLoginError] = useState("");

    // --- Visitor & Prayer State ---
    const [visitorId, setVisitorId] = useState(localStorage.getItem('cprn-visitor-id'));
    const [prayedIncidents, setPrayedIncidents] = useState(new Set());

    const PAGE_SIZE = 12;

    // --- Hash Utility (matching setup_admin.py) ---
    async function sha256(message) {
        const msgBuffer = new TextEncoder().encode(message);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    // --- Unified Logging Utility ---
    const logEvent = useCallback(async (name, type = 'FRONTEND', severity = 'INFO', metadata = {}) => {
        try {
            await supabaseClient.from('system_events').insert([{
                event_name: name,
                event_type: type,
                severity: severity,
                visitor_id: localStorage.getItem('cprn-visitor-id'),
                metadata: metadata
            }]);
        } catch (e) {
            console.error("Logging failed:", e);
        }
    }, []);

    // --- Auth Handlers ---
    const handleLogin = async (username, password) => {
        const hash = await sha256(password);
        const { data, error } = await supabaseClient
            .from('dashboard_users')
            .select('*')
            .eq('username', username)
            .eq('password_hash', hash)
            .single();

        if (data) {
            setIsLoggedIn(true);
            localStorage.setItem('cprn-logged-in', 'true');
            setLoginError("");
            setAdminView('sources');
        } else {
            setLoginError("Invalid credentials.");
        }
    };

    const handleLogout = () => {
        setIsLoggedIn(false);
        localStorage.removeItem('cprn-logged-in');
        setAdminView('none');
    };

    // --- Helper: Strip HTML ---
    const stripHtml = (html) => {
        let doc = new Error().stack ? new DOMParser().parseFromString(html, 'text/html') : null;
        return doc ? doc.body.textContent || "" : html.replace(/<[^>]*>?/gm, '');
    };

    // --- Helper: Simple Markdown (Bold only for AI) ---
    const renderMarkdown = (text) => {
        if (!text) return "";
        // Replace **text** with <strong>text</strong>
        const parts = text.split(/(\*\*.*?\*\*)/g);
        return parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={i} style={{ color: 'var(--text-primary)' }}>{part.slice(2, -2)}</strong>;
            }
            return part;
        });
    };

    // --- Theme Toggle ---
    useEffect(() => {
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('cprn-theme', theme);
    }, [theme]);

    const toggleTheme = () => setTheme(prev => prev === 'light' ? 'dark' : 'light');

    // --- Visitor & Connection Initialization ---
    useEffect(() => {
        // 1. Ensure Visitor ID exists
        let vid = localStorage.getItem('cprn-visitor-id');
        if (!vid) {
            vid = crypto.randomUUID();
            localStorage.setItem('cprn-visitor-id', vid);
        }
        setVisitorId(vid);

        // 2. Fetch User's Prayers
        const fetchUserPrayers = async () => {
            const { data } = await supabaseClient
                .from('incidents_prayers')
                .select('incident_id')
                .eq('visitor_id', vid);
            if (data) {
                setPrayedIncidents(new Set(data.map(p => p.incident_id)));
            }
        };
        if (vid) {
            logEvent('page_view', 'FRONTEND', 'INFO', { url: window.location.href });
        }
    }, [logEvent]);

    // --- Tracking Search ---
    useEffect(() => {
        if (searchQuery) {
            const timer = setTimeout(() => {
                logEvent('search_query', 'FRONTEND', 'INFO', { query: searchQuery });
            }, 1000); // Log after 1s of typing
            return () => clearTimeout(timer);
        }
    }, [searchQuery, logEvent]);

    // --- Supabase Interaction ---
    const fetchIncidents = useCallback(async (isNewSearch = false) => {
        setLoading(true);
        const start = isNewSearch ? 0 : page * PAGE_SIZE;
        const end = start + PAGE_SIZE - 1;

        let query = supabaseClient
            .from('incidents')
            .select('*', { count: 'exact' })
            .gte('incident_date', '2026-01-01')
            .order('incident_date', { ascending: false })
            .range(start, end);

        if (searchQuery) {
            query = query.or(`title.ilike.%${searchQuery}%,description.ilike.%${searchQuery}%,location_raw.ilike.%${searchQuery}%`);
        }

        const { data, error, count } = await query;

        if (error) {
            console.error("Fetch Error:", error);
        } else {
            setIncidents(prev => isNewSearch ? data : [...prev, ...data]);
            setHasMore(incidents.length + data.length < (count || 0));
            setInitialSync(true);
        }
        setLoading(false);
    }, [page, searchQuery]);

    useEffect(() => {
        fetchIncidents(true);
    }, [searchQuery]);

    useEffect(() => {
        if (page > 0) fetchIncidents();
    }, [page]);

    // Intersection Observer for Infinite Scroll
    const observer = useRef();
    const lastIncidentRef = useCallback(node => {
        if (loading) return;
        if (observer.current) observer.current.disconnect();
        observer.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore) {
                setPage(prev => prev + 1);
            }
        });
        if (node) observer.current.observe(node);
    }, [loading, hasMore]);

    // Format Date
    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    };

    // --- Prayer Handler ---
    const handlePray = async (incidentId) => {
        if (prayedIncidents.has(incidentId)) return;

        const { error } = await supabaseClient
            .from('incidents_prayers')
            .insert([{ incident_id: incidentId, visitor_id: visitorId }]);

        if (!error) {
            setPrayedIncidents(prev => new Set([...prev, incidentId]));
            // Optimistically update the UI count for the selected incident if it's open
            if (selectedIncident && selectedIncident.id === incidentId) {
                setSelectedIncident(prev => ({ ...prev, prayer_count: (prev.prayer_count || 0) + 1 }));
            }
            // Update the count in the main list
            setIncidents(prev => prev.map(inc =>
                inc.id === incidentId ? { ...inc, prayer_count: (inc.prayer_count || 0) + 1 } : inc
            ));
            logEvent('prayer_committed', 'FRONTEND', 'INFO', { incident_id: incidentId });
        } else {
            logEvent('prayer_failed', 'ERROR', 'ERROR', { incident_id: incidentId, error: error.message });
        }
    };

    // --- Sub-components for Admin ---
    const AdminSources = () => {
        const [sources, setSources] = useState([]);
        const [newSource, setNewSource] = useState({ name: '', url_or_handle: '', source_type: 'rss' });

        const fetchSources = async () => {
            const { data } = await supabaseClient.from('crawler_sources').select('*').order('name');
            setSources(data);
        };

        useEffect(() => { fetchSources(); }, []);

        const toggleSource = async (id, currentStatus) => {
            await supabaseClient.from('crawler_sources').update({ is_active: !currentStatus }).eq('id', id);
            fetchSources();
        };

        const deleteSource = async (id) => {
            if (confirm("Delete this source?")) {
                await supabaseClient.from('crawler_sources').delete().eq('id', id);
                fetchSources();
            }
        };

        const addSource = async () => {
            await supabaseClient.from('crawler_sources').insert([newSource]);
            setNewSource({ name: '', url_or_handle: '', source_type: 'rss' });
            fetchSources();
        };

        return (
            <div>
                <h3>Configure Data Sources</h3>
                <div className="admin-table-container">
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Type</th>
                                <th>URL / Handle</th>
                                <th>Active</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sources.map(s => (
                                <tr key={s.id}>
                                    <td>{s.name}</td>
                                    <td><span className="badge">{s.source_type}</span></td>
                                    <td>{s.url_or_handle}</td>
                                    <td>
                                        <input type="checkbox" checked={s.is_active} onChange={() => toggleSource(s.id, s.is_active)} />
                                    </td>
                                    <td>
                                        <button className="btn-icon" onClick={() => deleteSource(s.id)}>
                                            <i data-lucide="trash-2"></i>
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                    <h4>Add New Source</h4>
                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                        <input className="form-input" style={{ flex: 1 }} placeholder="Name (e.g. AsiaNews)" value={newSource.name} onChange={e => setNewSource({ ...newSource, name: e.target.value })} />
                        <input className="form-input" style={{ flex: 2 }} placeholder="URL or X Handle" value={newSource.url_or_handle} onChange={e => setNewSource({ ...newSource, url_or_handle: e.target.value })} />
                        <select className="form-input" style={{ flex: 1 }} value={newSource.source_type} onChange={e => setNewSource({ ...newSource, source_type: e.target.value })}>
                            <option value="rss">RSS Feed</option>
                            <option value="social">X (Twitter) Handle</option>
                        </select>
                        <button className="btn-action" onClick={addSource}>Add Source</button>
                    </div>
                </div>
            </div>
        );
    };

    const AdminIncidents = () => {
        const [showAddForm, setShowAddForm] = useState(false);
        const [newInc, setNewInc] = useState({
            title: '',
            description: '',
            location_raw: 'India',
            incident_date: new Date().toISOString().split('T')[0],
            sources: []
        });

        const deleteIncident = async (id) => {
            if (confirm("Permanent delete?")) {
                await supabaseClient.from('incidents').delete().eq('id', id);
                fetchIncidents(true);
            }
        };

        const addIncident = async () => {
            const data = {
                ...newInc,
                is_verified: true,
                sources: [{ name: 'Manual Entry', url: '#' }]
            };
            await supabaseClient.from('incidents').insert([data]);
            setNewInc({ title: '', description: '', location_raw: 'India', incident_date: new Date().toISOString().split('T')[0], sources: [] });
            setShowAddForm(false);
            fetchIncidents(true);
        };

        return (
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3>Manage Incidents</h3>
                    <button className="btn-read-more" onClick={() => setShowAddForm(!showAddForm)}>
                        {showAddForm ? 'Cancel' : 'Add Manual Report'}
                    </button>
                </div>

                {showAddForm && (
                    <div style={{ background: 'var(--bg-secondary)', padding: '2rem', borderRadius: '12px', marginBottom: '2rem', border: '1px solid var(--accent-gold)' }}>
                        <h4>New Incident Report</h4>
                        <div className="form-group">
                            <label className="form-label">Title</label>
                            <input className="form-input" value={newInc.title} onChange={e => setNewInc({ ...newInc, title: e.target.value })} />
                        </div>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Location (State/City)</label>
                                <input className="form-input" value={newInc.location_raw} onChange={e => setNewInc({ ...newInc, location_raw: e.target.value })} />
                            </div>
                            <div className="form-group" style={{ flex: 1 }}>
                                <label className="form-label">Incident Date</label>
                                <input className="form-input" type="date" value={newInc.incident_date} onChange={e => setNewInc({ ...newInc, incident_date: e.target.value })} />
                            </div>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Description</label>
                            <textarea className="form-input" style={{ minHeight: '150px' }} value={newInc.description} onChange={e => setNewInc({ ...newInc, description: e.target.value })}></textarea>
                        </div>
                        <button className="btn-read-more" onClick={addIncident}>Publish Report</button>
                    </div>
                )}

                <div className="admin-table-container">
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Title</th>
                                <th>Location</th>
                                <th>Verified</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {incidents.map(inc => (
                                <tr key={inc.id}>
                                    <td>{formatDate(inc.incident_date)}</td>
                                    <td>{inc.title.substring(0, 50)}...</td>
                                    <td>{inc.location_raw}</td>
                                    <td>{inc.is_verified ? '✅' : '⏳'}</td>
                                    <td>
                                        <button className="btn-icon" onClick={() => deleteIncident(inc.id)}>
                                            <i data-lucide="trash-2"></i>
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    const AdminUsers = () => {
        const [users, setUsers] = useState([]);
        const [newUser, setNewUser] = useState({ username: '', password: '' });

        const fetchUsers = async () => {
            const { data } = await supabaseClient.from('dashboard_users').select('id, username, created_at');
            setUsers(data);
        };

        useEffect(() => { fetchUsers(); }, []);

        const addUser = async () => {
            const hash = await sha256(newUser.password);
            await supabaseClient.from('dashboard_users').insert([{ username: newUser.username, password_hash: hash }]);
            setNewUser({ username: '', password: '' });
            fetchUsers();
        };

        return (
            <div>
                <h3>Authenticated Users</h3>
                <div className="admin-table-container">
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Joined</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {users.map(u => (
                                <tr key={u.id}>
                                    <td>{u.username}</td>
                                    <td>{formatDate(u.created_at)}</td>
                                    <td>
                                        {u.username !== 'admin' && (
                                            <button className="btn-icon" onClick={async () => {
                                                if (confirm("Remove user?")) {
                                                    await supabaseClient.from('dashboard_users').delete().eq('id', u.id);
                                                    fetchUsers();
                                                }
                                            }}>
                                                <i data-lucide="user-minus"></i>
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px', marginTop: '1rem' }}>
                    <h4>Add Operator</h4>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <input className="form-input" placeholder="Username" value={newUser.username} onChange={e => setNewUser({ ...newUser, username: e.target.value })} />
                        <input className="form-input" type="password" placeholder="Password" value={newUser.password} onChange={e => setNewUser({ ...newUser, password: e.target.value })} />
                        <button className="btn-action" onClick={addUser}>Create User</button>
                    </div>
                </div>
            </div>
        );
    };

    const AdminLogs = () => {
        const [logs, setLogs] = useState([]);

        const fetchLogs = async () => {
            const { data } = await supabaseClient
                .from('system_events')
                .select('*')
                .order('created_at', { ascending: false })
                .limit(100);
            setLogs(data || []);
        };

        useEffect(() => { fetchLogs(); }, []);

        return (
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3>System Operations & Analytics</h3>
                    <button className="btn-icon" onClick={fetchLogs} title="Refresh Logs">
                        <i data-lucide="refresh-cw"></i>
                    </button>
                </div>
                <div className="admin-table-container">
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Timestamp</th>
                                <th>Type</th>
                                <th>Event</th>
                                <th>Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            {logs.map(log => (
                                <tr key={log.id}>
                                    <td style={{ fontSize: '0.8rem', whiteSpace: 'nowrap' }}>
                                        {new Date(log.created_at).toLocaleString()}
                                    </td>
                                    <td>
                                        <span className="badge" style={{
                                            background: log.severity === 'ERROR' ? 'var(--accent-red)' :
                                                log.severity === 'WARNING' ? 'orange' : 'var(--bg-tertiary)',
                                            color: log.severity === 'ERROR' ? 'white' : 'inherit'
                                        }}>
                                            {log.event_type}
                                        </span>
                                    </td>
                                    <td style={{ fontWeight: 600 }}>{log.event_name}</td>
                                    <td style={{ fontSize: '0.8rem', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {JSON.stringify(log.metadata)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    const Login = () => {
        const [u, setU] = useState("");
        const [p, setP] = useState("");
        return (
            <div className="login-container">
                <h2 style={{ marginBottom: '1.5rem', textAlign: 'center' }}>Mission Control Login</h2>
                {loginError && <p style={{ color: 'var(--accent-red)', fontSize: '0.8rem', marginBottom: '1rem' }}>{loginError}</p>}
                <div className="form-group">
                    <label className="form-label">Username</label>
                    <input className="form-input" value={u} onChange={e => setU(e.target.value)} />
                </div>
                <div className="form-group">
                    <label className="form-label">Password</label>
                    <input className="form-input" type="password" value={p} onChange={e => setP(e.target.value)} />
                </div>
                <button className="btn-read-more" style={{ width: '100%' }} onClick={() => handleLogin(u, p)}>Access Dashboard</button>
                <button className="btn-action" style={{ width: '100%', marginTop: '0.5rem', border: 'none' }} onClick={() => setAdminView('none')}>Back to Portal</button>
            </div>
        );
    };

    if (!initialSync) {
        return (
            <div className="initial-loader">
                <div className="spinner"></div>
                <p>Loading CPRN Mission Control...</p>
            </div>
        );
    }

    if (adminView !== 'none' && !isLoggedIn) {
        return <Login />;
    }

    return (
        <div className="app-container">
            <header className="main-header">
                <div className="logo" onClick={() => setAdminView('none')} style={{ cursor: 'pointer' }}>
                    <span className="logo-text">CPRN<span className="logo-accent">.</span></span>
                    {adminView !== 'none' && <span className="badge" style={{ marginLeft: '1rem', background: 'var(--accent-red)', color: 'white' }}>Mission Control</span>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                    {isLoggedIn && adminView === 'none' && (
                        <button className="btn-action" onClick={() => setAdminView('sources')}>
                            <i data-lucide="layout-dashboard" style={{ width: '16px', marginRight: '0.5rem' }}></i>
                            Dashboard
                        </button>
                    )}
                    {isLoggedIn && adminView !== 'none' && (
                        <button className="btn-action" style={{ border: 'none', color: 'var(--accent-red)' }} onClick={handleLogout}>
                            Logout
                        </button>
                    )}
                    {!isLoggedIn && adminView === 'none' && (
                        <button className="btn-icon" onClick={() => setAdminView('login')} title="Operator Login">
                            <i data-lucide="lock" style={{ width: '16px' }}></i>
                        </button>
                    )}
                    <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle Theme">
                        <i data-lucide={theme === 'light' ? "moon" : "sun"}></i>
                    </button>
                </div>
            </header>

            {adminView === 'none' ? (
                <>
                    <div className="search-wrapper">
                        <i data-lucide="search" className="search-icon"></i>
                        <input
                            type="text"
                            className="search-input"
                            placeholder="Search incidents or locations..."
                            value={searchQuery}
                            onChange={(e) => {
                                setSearchQuery(e.target.value);
                                setPage(0);
                            }}
                        />
                    </div>

                    <main className="incident-grid">
                        {incidents.map((incident, index) => {
                            const isLast = incidents.length === index + 1;
                            const cleanDesc = stripHtml(incident.description);

                            return (
                                <div key={incident.id} className="card" ref={isLast ? lastIncidentRef : null}>
                                    {incident.image_url && (
                                        <div className="card-image-wrapper">
                                            <img src={incident.image_url} alt={incident.title} className="card-image" loading="lazy" />
                                        </div>
                                    )}
                                    <div className="card-header">
                                        <span className="date-badge">{formatDate(incident.incident_date)}</span>
                                        <div className="source-badges">
                                            {incident.sources.map((s, i) => (
                                                <span key={i} className="badge">{s.name}</span>
                                            ))}
                                        </div>
                                    </div>

                                    <h2 className="card-title">{incident.title}</h2>

                                    <div className="location-tag">
                                        <i data-lucide="map-pin" className="location-icon"></i>
                                        {incident.location_raw}
                                    </div>

                                    <p className="card-description">{cleanDesc}</p>

                                    <div className="card-footer">
                                        <div className="prayer-badge">
                                            <i data-lucide="heart" className={prayedIncidents.has(incident.id) ? "prayer-pulse" : ""} style={{ width: '14px', fill: prayedIncidents.has(incident.id) ? 'var(--accent-gold)' : 'none' }}></i>
                                            {incident.prayer_count || 0} Praying
                                        </div>
                                        <button className="btn-read-more" onClick={() => {
                                            setSelectedIncident(incident);
                                            logEvent('incident_view', 'FRONTEND', 'INFO', { incident_id: incident.id, title: incident.title });
                                        }}>
                                            Details & Analysis
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </main>
                </>
            ) : (
                <div className="admin-portal">
                    <div className="admin-nav">
                        <div className={`nav-item ${adminView === 'sources' ? 'active' : ''}`} onClick={() => setAdminView('sources')}>
                            <i data-lucide="refresh-ccw" style={{ width: '14px', marginRight: '0.5rem' }}></i> Sources
                        </div>
                        <div className={`nav-item ${adminView === 'incidents' ? 'active' : ''}`} onClick={() => setAdminView('incidents')}>
                            <i data-lucide="alert-circle" style={{ width: '14px', marginRight: '0.5rem' }}></i> Manage Reports
                        </div>
                        <div className={`nav-item ${adminView === 'users' ? 'active' : ''}`} onClick={() => setAdminView('users')}>
                            <i data-lucide="users" style={{ width: '14px', marginRight: '0.5rem' }}></i> Team
                        </div>
                        <div className={`nav-item ${adminView === 'logs' ? 'active' : ''}`} onClick={() => setAdminView('logs')}>
                            <i data-lucide="activity" style={{ width: '14px', marginRight: '0.5rem' }}></i> System Logs
                        </div>
                        <div className="nav-item" onClick={() => setAdminView('none')} style={{ marginLeft: 'auto' }}>
                            View Public Portal
                        </div>
                    </div>

                    <div className="admin-content">
                        {adminView === 'sources' && <AdminSources />}
                        {adminView === 'incidents' && <AdminIncidents />}
                        {adminView === 'users' && <AdminUsers />}
                        {adminView === 'logs' && <AdminLogs />}
                    </div>
                </div>
            )}

            {loading && (
                <div className="scroll-trigger">
                    <div className="spinner" style={{ margin: '0 auto' }}></div>
                </div>
            )}

            {!hasMore && incidents.length > 0 && (
                <div className="scroll-trigger">
                    <p style={{ opacity: 0.5, fontSize: '0.9rem' }}>No further reports found.</p>
                </div>
            )}

            {selectedIncident && (
                <div className="modal-overlay" onClick={() => setSelectedIncident(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <button
                            className="btn-icon"
                            style={{
                                position: 'absolute',
                                top: '1rem',
                                right: '1rem',
                                background: 'var(--bg-tertiary)',
                                zIndex: 10,
                                width: '32px',
                                height: '32px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                borderRadius: '50%'
                            }}
                            onClick={() => setSelectedIncident(null)}
                            title="Close"
                        >
                            <i data-lucide="x" style={{ width: '20px' }}></i>
                        </button>

                        <div style={{ marginBottom: '2rem' }}>
                            <div className="date-badge" style={{ marginBottom: '0.5rem' }}>{formatDate(selectedIncident.incident_date)}</div>
                            <h1 className="card-title" style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>{selectedIncident.title}</h1>
                            <div className="location-tag" style={{ fontSize: '1rem' }}>
                                <i data-lucide="map-pin" className="location-icon"></i> {selectedIncident.location_raw}
                            </div>
                        </div>

                        <div style={{ lineHeight: 1.8 }}>
                            <div className="prayer-count-modal">
                                <div className="prayer-count-number">{selectedIncident.prayer_count || 0}</div>
                                <div className="prayer-count-label">People standing in prayer</div>
                            </div>

                            <button
                                className={`btn-pray ${prayedIncidents.has(selectedIncident.id) ? 'active' : ''}`}
                                onClick={() => handlePray(selectedIncident.id)}
                                disabled={prayedIncidents.has(selectedIncident.id)}
                            >
                                <i data-lucide="heart" className={prayedIncidents.has(selectedIncident.id) ? "" : "prayer-pulse"}></i>
                                {prayedIncidents.has(selectedIncident.id) ? "You have committed to pray" : "I will pray for this"}
                            </button>

                            {selectedIncident.summary && (
                                <div className="summary-section" style={{
                                    background: 'var(--bg-secondary)',
                                    padding: '1.5rem',
                                    borderRadius: '12px',
                                    marginBottom: '2rem',
                                    borderLeft: '4px solid var(--accent-gold)',
                                    fontSize: '0.95rem'
                                }}>
                                    <h4 style={{ color: 'var(--accent-gold)', marginTop: 0, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <i data-lucide="sparkles" style={{ width: '16px' }}></i> AI Briefing
                                    </h4>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>
                                        {renderMarkdown(selectedIncident.summary)}
                                    </div>
                                </div>
                            )}

                            <h4 style={{ color: 'var(--accent-gold)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <i data-lucide="check-circle" style={{ width: '16px' }}></i> Verified Reporting Sources:
                            </h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                                {selectedIncident.sources.map((s, i) => (
                                    <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="badge" style={{ display: 'block', padding: '1rem', textAlign: 'left', textDecoration: 'none' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span>Access Original Report from <strong>{s.name}</strong></span>
                                            <i data-lucide="external-link" style={{ width: '16px' }}></i>
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);

// Refresh Icons
setInterval(() => {
    if (window.lucide) window.lucide.createIcons();
}, 200);
