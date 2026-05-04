import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FileText, Lightbulb, RefreshCw, Download, Printer,
    AlertTriangle, CheckCircle, Clock, Share2, FileDown,
    ChevronDown, Activity, Zap
} from 'lucide-react';

// ── Styles priorités ──
const PRIORITY_STYLES = {
    'URGENTE': { card: 'bg-rose-500/10 border-rose-500/30 border-l-4 border-l-rose-500', badge: 'bg-rose-500 text-white', icon: '🚨' },
    'HAUTE': { card: 'bg-amber-500/10 border-amber-500/30 border-l-4 border-l-amber-500', badge: 'bg-amber-500 text-white', icon: '⚠️' },
    'NORMALE': { card: 'bg-blue-500/10 border-blue-500/30 border-l-4 border-l-blue-500', badge: 'bg-blue-500 text-white', icon: 'ℹ️' },
    'haute': { card: 'bg-rose-500/10 border-rose-500/30 border-l-4 border-l-rose-500', badge: 'bg-rose-500 text-white', icon: '🚨' },
    'moyenne': { card: 'bg-amber-500/10 border-amber-500/30 border-l-4 border-l-amber-500', badge: 'bg-amber-500 text-white', icon: '⚠️' },
    'basse': { card: 'bg-emerald-500/10 border-emerald-500/30 border-l-4 border-l-emerald-500', badge: 'bg-emerald-500 text-white', icon: '✅' },
};

// Extraire priorité depuis texte suggestion
const extractPriority = (text) => {
    if (!text) return 'NORMALE';
    if (text.includes('URGENTE') || text.includes('urgente')) return 'URGENTE';
    if (text.includes('HAUTE') || text.includes('haute')) return 'HAUTE';
    return 'NORMALE';
};

// Extraire entité et action depuis texte suggestion
const parseSuggestion = (text, index) => {
    if (typeof text === 'object') return text;
    return {
        priorite: extractPriority(text),
        message: text.replace(/^\d+\.\s*/, '').replace(/\[PRIORITÉ:.*?\]\s*/i, ''),
        id: index,
    };
};

export default function Rapports({ apiBase }) {
    const [rapport, setRapport] = useState('');
    const [rapportAir, setRapportAir] = useState('');
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(false);
    const [loadingAir, setLoadingAir] = useState(false);
    const [date, setDate] = useState('');
    const [activeTab, setActiveTab] = useState('journalier');
    const [showExport, setShowExport] = useState(false);
    const [stats, setStats] = useState(null);
    const rapportRef = useRef(null);

    // ── Fetch données ──
    const fetchRapport = useCallback(async () => {
        setLoading(true);
        try {
            const [rRes, sRes, dRes] = await Promise.all([
                axios.get(`${apiBase}/rapport`),
                axios.get(`${apiBase}/suggestions`),
                axios.get(`${apiBase}/dashboard`).catch(() => ({ data: null })),
            ]);
            setRapport(rRes.data.rapport || '');
            setDate(rRes.data.date || new Date().toLocaleDateString('fr-FR'));
            const raw = sRes.data.suggestions || '';
            const lines = typeof raw === 'string'
                ? raw.split('\n').filter(l => l.trim() && !l.includes('SUGGESTIONS'))
                : Array.isArray(raw) ? raw : [];
            setSuggestions(lines.map((l, i) => parseSuggestion(l, i)));
            if (dRes.data) setStats(dRes.data);
        } catch (err) {
            console.error('Rapports fetch error:', err);
        } finally {
            setLoading(false);
        }
    }, [apiBase]);

    const fetchRapportAir = useCallback(async () => {
        setLoadingAir(true);
        try {
            const res = await axios.get(`${apiBase}/rapport/air`);
            setRapportAir(res.data.rapport || '');
        } catch (err) {
            console.error('Rapport air error:', err);
        } finally {
            setLoadingAir(false);
        }
    }, [apiBase]);

    useEffect(() => {
        fetchRapport();
        fetchRapportAir();
    }, [fetchRapport, fetchRapportAir]);

    // ── Impression ──
    const handlePrint = () => {
        const content = activeTab === 'journalier' ? rapport : rapportAir;
        const title = activeTab === 'journalier'
            ? `Rapport Journalier — Neo-Sousse 2030 — ${date}`
            : `Rapport Qualité de l'Air — Neo-Sousse 2030 — ${date}`;

        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>${title}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #1a1a2e;
            background: white;
            padding: 40px;
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            border-bottom: 3px solid #4f46e5;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .logo {
            font-size: 10px;
            font-weight: 900;
            letter-spacing: 4px;
            color: #4f46e5;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        h1 {
            font-size: 24px;
            font-weight: 800;
            color: #1a1a2e;
            margin-bottom: 6px;
        }
        .meta {
            font-size: 12px;
            color: #6b7280;
            display: flex;
            gap: 20px;
        }
        .content {
            font-size: 13px;
            line-height: 1.9;
            color: #374151;
            white-space: pre-wrap;
        }
        .section-title {
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #4f46e5;
            margin: 24px 0 12px;
            padding-bottom: 6px;
            border-bottom: 1px solid #e5e7eb;
        }
        .suggestions { margin-top: 30px; }
        .suggestion {
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 4px solid #4f46e5;
            background: #f8fafc;
            font-size: 12px;
        }
        .suggestion.urgente { border-left-color: #ef4444; background: #fff5f5; }
        .suggestion.haute   { border-left-color: #f59e0b; background: #fffbeb; }
        .priority-badge {
            display: inline-block;
            font-size: 9px;
            font-weight: 900;
            letter-spacing: 1px;
            text-transform: uppercase;
            padding: 2px 8px;
            border-radius: 20px;
            background: #4f46e5;
            color: white;
            margin-bottom: 6px;
        }
        .priority-badge.urgente { background: #ef4444; }
        .priority-badge.haute   { background: #f59e0b; color: #1a1a2e; }
        .footer {
            margin-top: 40px;
            padding-top: 16px;
            border-top: 1px solid #e5e7eb;
            font-size: 10px;
            color: #9ca3af;
            display: flex;
            justify-content: space-between;
        }
        .kpis {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin: 20px 0;
        }
        .kpi {
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .kpi-value { font-size: 24px; font-weight: 900; color: #4f46e5; }
        .kpi-label { font-size: 10px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; }
        @media print {
            body { padding: 20px; }
            button { display: none !important; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">Smart City Platform</div>
        <h1>${title}</h1>
        <div class="meta">
            <span>📅 Généré le ${date}</span>
            <span>🏙️ Neo-Sousse 2030</span>
            <span>🤖 Propulsé par ARIA IA</span>
        </div>
    </div>

    ${stats ? `
    <div class="section-title">Indicateurs Clés</div>
    <div class="kpis">
        <div class="kpi">
            <div class="kpi-value">${stats.capteurs?.actifs ?? '—'}</div>
            <div class="kpi-label">Capteurs Actifs</div>
        </div>
        <div class="kpi">
            <div class="kpi-value">${stats.capteurs?.hors_service ?? '—'}</div>
            <div class="kpi-label">Hors Service</div>
        </div>
        <div class="kpi">
            <div class="kpi-value">${stats.interventions?.en_cours ?? '—'}</div>
            <div class="kpi-label">Interventions</div>
        </div>
        <div class="kpi">
            <div class="kpi-value">${stats.citoyens?.score_moyen ?? '—'}</div>
            <div class="kpi-label">Score Éco.</div>
        </div>
    </div>` : ''}

    <div class="section-title">Rapport Complet</div>
    <div class="content">${content.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>

    ${suggestions.length > 0 ? `
    <div class="suggestions">
        <div class="section-title">Suggestions d'Actions (${suggestions.length})</div>
        ${suggestions.map(s => `
            <div class="suggestion ${(s.priorite || '').toLowerCase()}">
                <div class="priority-badge ${(s.priorite || '').toLowerCase()}">${s.priorite || 'INFO'}</div>
                <div>${(s.message || '').replace(/</g, '&lt;')}</div>
            </div>
        `).join('')}
    </div>` : ''}

    <div class="footer">
        <span>© 2030 Smart City Neo-Sousse — Plateforme de Gestion Urbaine</span>
        <span>Rapport confidentiel — Usage interne uniquement</span>
    </div>

    <script>window.onload = () => { window.print(); window.onafterprint = () => window.close(); }</script>
</body>
</html>`);
        printWindow.document.close();
    };

    // ── Téléchargement TXT ──
    const handleDownloadTXT = () => {
        const content = activeTab === 'journalier' ? rapport : rapportAir;
        const title = activeTab === 'journalier' ? 'rapport_journalier' : 'rapport_qualite_air';

        const fullText = [
            '═'.repeat(60),
            `  SMART CITY NEO-SOUSSE 2030`,
            `  ${title.replace(/_/g, ' ').toUpperCase()}`,
            `  Généré le ${date}`,
            '═'.repeat(60),
            '',
            content,
            '',
            suggestions.length > 0 ? '─'.repeat(60) : '',
            suggestions.length > 0 ? 'SUGGESTIONS D\'ACTIONS :' : '',
            ...suggestions.map((s, i) => `${i + 1}. [${s.priorite}] ${s.message}`),
            '',
            '─'.repeat(60),
            `Rapport généré automatiquement par ARIA — ${new Date().toLocaleString('fr-FR')}`,
        ].join('\n');

        const blob = new Blob([fullText], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title}_${date.replace(/\//g, '-')}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        setShowExport(false);
    };

    // ── Téléchargement JSON ──
    const handleDownloadJSON = () => {
        const data = {
            metadata: {
                titre: activeTab === 'journalier' ? 'Rapport Journalier' : 'Rapport Qualité Air',
                date,
                genere_par: 'ARIA — Smart City Neo-Sousse 2030',
                timestamp: new Date().toISOString(),
            },
            rapport: activeTab === 'journalier' ? rapport : rapportAir,
            suggestions: suggestions,
            statistiques: stats,
        };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `rapport_${date.replace(/\//g, '-')}.json`;
        a.click();
        URL.revokeObjectURL(url);
        setShowExport(false);
    };

    const currentContent = activeTab === 'journalier' ? rapport : rapportAir;
    const currentLoading = activeTab === 'journalier' ? loading : loadingAir;

    return (
        <div className="space-y-6 max-w-6xl mx-auto">

            {/* ── Header ── */}
            <div className="flex justify-between items-start">
                <div>
                    <h2 className="text-3xl font-extrabold text-white flex items-center gap-3">
                        <FileText className="text-indigo-400 w-8 h-8" />
                        Rapports Stratégiques IA
                    </h2>
                    <p className="text-gray-500 mt-1 text-sm">
                        Synthèse décisionnelle générée par ARIA — {date}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    {/* Bouton Régénérer */}
                    <button onClick={activeTab === 'journalier' ? fetchRapport : fetchRapportAir}
                        disabled={currentLoading}
                        className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all disabled:opacity-50 text-sm">
                        <RefreshCw className={`w-4 h-4 ${currentLoading ? 'animate-spin' : ''}`} />
                        Régénérer
                    </button>

                    {/* Menu Export */}
                    <div className="relative">
                        <button
                            onClick={() => setShowExport(v => !v)}
                            className="flex items-center gap-2 px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl font-bold transition-all text-sm border border-gray-700">
                            <Download className="w-4 h-4 text-indigo-400" />
                            Exporter
                            <ChevronDown className={`w-4 h-4 transition-transform ${showExport ? 'rotate-180' : ''}`} />
                        </button>

                        <AnimatePresence>
                            {showExport && (
                                <motion.div
                                    initial={{ opacity: 0, y: -8, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: -8, scale: 0.95 }}
                                    className="absolute right-0 top-12 w-52 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                                    <button onClick={handlePrint}
                                        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-800 transition-colors text-sm text-gray-200">
                                        <Printer className="w-4 h-4 text-indigo-400" />
                                        Imprimer le rapport
                                    </button>
                                    <button onClick={handleDownloadTXT}
                                        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-800 transition-colors text-sm text-gray-200">
                                        <FileDown className="w-4 h-4 text-emerald-400" />
                                        Télécharger (.txt)
                                    </button>
                                    <button onClick={handleDownloadJSON}
                                        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-800 transition-colors text-sm text-gray-200">
                                        <FileDown className="w-4 h-4 text-amber-400" />
                                        Télécharger (.json)
                                    </button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* ── KPIs stats ── */}
            {stats && (
                <div className="grid grid-cols-4 gap-4">
                    {[
                        { label: 'Capteurs actifs', value: stats.capteurs?.actifs, color: 'emerald', icon: '📡' },
                        { label: 'Hors service', value: stats.capteurs?.hors_service, color: 'red', icon: '🚨' },
                        { label: 'Interventions', value: stats.interventions?.en_cours, color: 'amber', icon: '🔧' },
                        { label: 'Score éco. moyen', value: `${stats.citoyens?.score_moyen ?? '—'}/100`, color: 'blue', icon: '🌿' },
                    ].map(k => (
                        <div key={k.label}
                            className={`bg-gray-900/60 border border-${k.color}-500/20 rounded-xl p-4 flex items-center gap-3`}>
                            <span className="text-2xl">{k.icon}</span>
                            <div>
                                <div className={`text-xl font-bold text-${k.color}-400`}>{k.value ?? '—'}</div>
                                <div className="text-xs text-gray-500">{k.label}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* ── Tabs ── */}
            <div className="flex gap-2">
                {[
                    { id: 'journalier', label: 'Rapport Journalier', icon: Activity },
                    { id: 'air', label: 'Qualité de l\'Air', icon: Zap },
                ].map(tab => {
                    const Icon = tab.icon;
                    return (
                        <button key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${activeTab === tab.id
                                ? 'bg-indigo-600 text-white'
                                : 'bg-gray-800 text-gray-400 hover:text-gray-200'
                                }`}>
                            <Icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* ── Contenu principal ── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Rapport */}
                <div className="lg:col-span-2">
                    <div className="bg-gray-900/60 border border-gray-700/40 rounded-2xl overflow-hidden">
                        {/* Toolbar rapport */}
                        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-gray-900/40">
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                Généré par ARIA — {date}
                            </div>
                            <div className="flex gap-2">
                                <button onClick={handlePrint}
                                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition-colors">
                                    <Printer className="w-3 h-3" /> Imprimer
                                </button>
                                <button onClick={handleDownloadTXT}
                                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition-colors">
                                    <Download className="w-3 h-3" /> .txt
                                </button>
                                <button onClick={handleDownloadJSON}
                                    className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition-colors">
                                    <Download className="w-3 h-3" /> .json
                                </button>
                            </div>
                        </div>

                        {/* Contenu rapport */}
                        <div ref={rapportRef} className="p-8 min-h-[500px]">
                            {currentLoading ? (
                                <div className="space-y-4">
                                    {[1, 2, 3, 4, 5].map(i => (
                                        <div key={i} className={`h-4 bg-gray-800 rounded animate-pulse`}
                                            style={{ width: `${60 + Math.random() * 40}%` }} />
                                    ))}
                                </div>
                            ) : currentContent ? (
                                <div className="whitespace-pre-wrap text-sm text-gray-300 leading-relaxed font-mono">
                                    {currentContent}
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-64 text-gray-600">
                                    <FileText className="w-12 h-12 mb-4 opacity-30" />
                                    <p className="text-sm">Cliquez sur Régénérer pour charger le rapport</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Panel suggestions */}
                <div className="space-y-4">
                    <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-2xl p-5">
                        <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <Lightbulb className="w-4 h-4" />
                            Suggestions d'Actions
                            {suggestions.length > 0 && (
                                <span className="ml-auto bg-indigo-500 text-white text-[10px] px-2 py-0.5 rounded-full">
                                    {suggestions.length}
                                </span>
                            )}
                        </h3>

                        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                            {suggestions.length > 0 ? suggestions.map((s, i) => {
                                const style = PRIORITY_STYLES[s.priorite] || PRIORITY_STYLES['NORMALE'];
                                return (
                                    <motion.div key={i}
                                        initial={{ opacity: 0, x: 10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.05 }}
                                        className={`p-3 rounded-xl border ${style.card}`}>
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-sm">{style.icon}</span>
                                            <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${style.badge}`}>
                                                {s.priorite}
                                            </span>
                                            <span className="text-[9px] text-gray-600 ml-auto">#{i + 1}</span>
                                        </div>
                                        <p className="text-xs text-gray-300 leading-relaxed">{s.message}</p>
                                        <div className="flex gap-2 mt-2">
                                            <button className="text-[9px] font-bold bg-white/5 hover:bg-white/10 px-2 py-1 rounded transition-colors">
                                                Assigner
                                            </button>
                                            <button className="text-[9px] font-bold bg-white/5 hover:bg-white/10 px-2 py-1 rounded transition-colors">
                                                Ignorer
                                            </button>
                                        </div>
                                    </motion.div>
                                );
                            }) : (
                                <div className="text-center py-8 text-gray-600 text-xs">
                                    <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-30" />
                                    Aucune suggestion disponible
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Stats rapport */}
                    <div className="bg-gray-900/60 border border-gray-700/40 rounded-xl p-4">
                        <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3">
                            Résumé du rapport
                        </h4>
                        <div className="space-y-2 text-xs">
                            <div className="flex justify-between">
                                <span className="text-gray-500">Mots</span>
                                <span className="text-white font-mono">
                                    {currentContent ? currentContent.split(/\s+/).filter(Boolean).length : 0}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Suggestions</span>
                                <span className="text-white font-mono">{suggestions.length}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Urgentes</span>
                                <span className="text-red-400 font-mono">
                                    {suggestions.filter(s => s.priorite === 'URGENTE').length}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">Date</span>
                                <span className="text-indigo-400 font-mono">{date}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}