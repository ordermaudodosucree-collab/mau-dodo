import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import './Dashboard.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [stats, setStats]       = useState(null);
  const [periode, setPeriode]   = useState('mois');
  const [chargement, setChargement] = useState(true);

  const chargerStats = useCallback(async () => {
    try {
      setChargement(true);
      const res = await axios.get(`${API}/dashboard?periode=${periode}`);
      setStats(res.data);
    } catch (e) {
      toast.error('Impossible de charger le dashboard');
    } finally {
      setChargement(false);
    }
  }, [periode]);

useEffect(() => {
  chargerStats();
  // Rafraîchissement automatique toutes les 30 secondes
  const interval = setInterval(chargerStats, 30000);
  return () => clearInterval(interval);
}, [chargerStats]);

  const formatCA = (montant) => {
    if (!montant) return '0 MUR';
    return new Intl.NumberFormat('fr-FR').format(montant) + ' MUR';
  };

  const maxCA = stats?.ca_par_jour?.length
    ? Math.max(...stats.ca_par_jour.map(d => d.ca), 1)
    : 1;

  if (chargement) return <div className="chargement">Chargement du dashboard...</div>;

  return (
    <div className="dashboard">
      {/* HEADER */}
      <div className="dash-header">
        <h2 className="dash-title">📊 Dashboard</h2>
        <div className="periode-selector">
          {['semaine', 'mois', 'annee'].map(p => (
            <button
              key={p}
              className={`periode-btn ${periode === p ? 'active' : ''}`}
              onClick={() => setPeriode(p)}
            >
              {p === 'semaine' ? 'Cette semaine' : p === 'mois' ? 'Ce mois' : 'Cette année'}
            </button>
          ))}
        </div>
      </div>

      {/* KPI CARDS */}
      <div className="kpi-grid">
        <div className="kpi-card kpi-brun">
          <div className="kpi-icon">💰</div>
          <div className="kpi-value">{formatCA(stats?.ca_periode)}</div>
          <div className="kpi-label">CA sur la période</div>
          <div className="kpi-sub">Total : {formatCA(stats?.ca_total)}</div>
        </div>
        <div className="kpi-card kpi-vert">
          <div className="kpi-icon">📋</div>
          <div className="kpi-value">{stats?.nb_commandes_periode || 0}</div>
          <div className="kpi-label">Commandes sur la période</div>
          <div className="kpi-sub">Total : {stats?.nb_commandes_total || 0}</div>
        </div>
        <div className="kpi-card kpi-bleu">
          <div className="kpi-icon">🚚</div>
          <div className="kpi-value">{stats?.nb_livraisons_periode || 0}</div>
          <div className="kpi-label">Livraisons sur la période</div>
          <div className="kpi-sub">Total : {stats?.nb_livraisons_total || 0}</div>
        </div>
        <div className="kpi-card kpi-orange">
          <div className="kpi-icon">⚠️</div>
          <div className="kpi-value">{stats?.stocks_bas?.length || 0}</div>
          <div className="kpi-label">Produits en alerte stock</div>
          <div className="kpi-sub">Vérifier les stocks</div>
        </div>
      </div>

      <div className="dash-grid">
        {/* GRAPHIQUE CA PAR JOUR */}
        <div className="dash-card">
          <h3 className="dash-card-title">CA par jour (30 derniers jours)</h3>
          {stats?.ca_par_jour?.length === 0 ? (
            <div className="empty">Aucune donnée disponible</div>
          ) : (
            <div className="chart">
              {stats?.ca_par_jour?.map((d, i) => (
                <div className="bar-wrap" key={i}>
                  <div className="bar-label">{d.ca > 0 ? formatCA(d.ca).replace(' MUR','') : ''}</div>
                  <div
                    className="bar"
                    style={{ height: `${Math.max((d.ca / maxCA) * 160, 4)}px` }}
                    title={`${d.jour} : ${formatCA(d.ca)}`}
                  />
                  <div className="bar-date">{d.jour}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* TOP CLIENTS */}
        <div className="dash-card">
          <h3 className="dash-card-title">🏆 Top 5 clients</h3>
          {stats?.top_clients?.length === 0 ? (
            <div className="empty">Aucune donnée disponible</div>
          ) : (
            <div className="top-clients">
              {stats?.top_clients?.map((c, i) => (
                <div className="client-row" key={i}>
                  <div className="client-rank">#{i + 1}</div>
                  <div className="client-name">{c.client}</div>
                  <div className="client-ca">{formatCA(c.ca)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* STOCKS EN ALERTE */}
        <div className="dash-card">
          <h3 className="dash-card-title">🚨 Alertes stock</h3>
          {stats?.stocks_bas?.length === 0 ? (
            <div className="empty ok">✅ Tous les stocks sont OK</div>
          ) : (
            <div className="alertes">
              {stats?.stocks_bas?.map((s, i) => (
                <div className="alerte-row" key={i}>
                  <div className="alerte-nom">{s.nom}</div>
                  <div className="alerte-qte">
                    <span className="qte-badge rouge">{s.quantite} unités</span>
                    <span className="seuil-info">seuil : {s.seuil}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
