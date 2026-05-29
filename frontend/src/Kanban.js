import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import './Kanban.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const STATUTS = [
  { key: 'recu',       label: 'Commande reçue',  couleur: '#378ADD', badge: 'badge-blue'  },
  { key: 'production', label: 'En production',    couleur: '#EF9F27', badge: 'badge-amber' },
  { key: 'livraison',  label: 'En livraison',     couleur: '#639922', badge: 'badge-green' },
];

export default function Kanban() {
  const [commandes, setCommandes]     = useState([]);
  const [recherche, setRecherche]     = useState('');
  const [chargement, setChargement]   = useState(true);

  // ── Charger les commandes ──────────────────────────────────────
  const chargerCommandes = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/commandes`);
      setCommandes(res.data);
    } catch (e) {
      toast.error('Impossible de charger les commandes');
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    chargerCommandes();
  }, [chargerCommandes]);

  // ── WebSocket — mises à jour temps réel ───────────────────────
  useEffect(() => {
    const wsUrl = API.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/ws`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'nouvelle_commande') {
        toast.success(`Nouvelle commande reçue : ${msg.reference} !`);
        chargerCommandes();
      } else if (msg.type === 'statut_change' || msg.type === 'produit_update') {
        chargerCommandes();
      }
    };

    return () => ws.close();
  }, [chargerCommandes]);

  // ── Changer statut ────────────────────────────────────────────
  const changerStatut = async (reference, nouveauStatut) => {
    try {
      await axios.patch(`${API}/commandes/${reference}/statut`, { statut: nouveauStatut });
      toast.success('Statut mis à jour !');
      chargerCommandes();
    } catch (e) {
      toast.error('Erreur lors du changement de statut');
    }
  };

  // ── Cocher/décocher un produit ────────────────────────────────
  const toggleProduit = async (produitId, fait) => {
    try {
      await axios.patch(`${API}/produits/${produitId}`, { fait });
      chargerCommandes();
    } catch (e) {
      toast.error('Erreur lors de la mise à jour du produit');
    }
  };

  // ── Filtrer les commandes selon la recherche ──────────────────
  const commandesFiltrees = commandes.filter(c => {
    if (!recherche) return true;
    const q = recherche.toLowerCase();
    return (
      c.reference?.toLowerCase().includes(q) ||
      c.client?.toLowerCase().includes(q) ||
      c.numero_commande?.toLowerCase().includes(q) ||
      c.produits?.some(p => p.nom?.toLowerCase().includes(q))
    );
  });

  const commandesDuStatut = (statut) =>
    commandesFiltrees.filter(c => c.statut === statut);

  // ── Progression d'une commande ────────────────────────────────
  const progression = (commande) => {
    if (!commande.produits?.length) return 0;
    const faits = commande.produits.filter(p => p.fait).length;
    return Math.round((faits / commande.produits.length) * 100);
  };

  // ── Bouton d'action selon statut ──────────────────────────────
  const prochainStatut = (statut) => {
    if (statut === 'recu')       return { label: 'Démarrer production ↗', next: 'production' };
    if (statut === 'production') return { label: 'Envoyer en livraison ↗', next: 'livraison' };
    if (statut === 'livraison')  return { label: 'Confirmer réception ↗', next: 'livre' };
    return null;
  };

  if (chargement) return <div className="chargement">Chargement des commandes...</div>;

  return (
    <div className="kanban">
      {/* ── HEADER ── */}
      <div className="header">
        <div className="logo"><span>Mau Dodo</span> Sucrée</div>
        <div className="stats">
          <div className="stat"><b>{commandes.length}</b> commandes</div>
          <div className="stat"><b>{new Date().toLocaleDateString('fr-FR')}</b></div>
        </div>
      </div>

      {/* ── BARRE DE RECHERCHE ── */}
      <div className="searchbar">
        <span className="search-icon">🔍</span>
        <input
          type="text"
          placeholder="Rechercher par référence, client ou produit…"
          value={recherche}
          onChange={e => setRecherche(e.target.value)}
        />
        {recherche && (
          <button className="clear-btn" onClick={() => setRecherche('')}>✕</button>
        )}
      </div>

      {/* ── COLONNES KANBAN ── */}
      <div className="colonnes">
        {STATUTS.map(statut => {
          const cartes = commandesDuStatut(statut.key);
          const action = prochainStatut(statut.key);

          return (
            <div className="colonne" key={statut.key}>
              <div className="colonne-header">
                <span className="colonne-titre">{statut.label}</span>
                <span className={`badge ${statut.badge}`}>{cartes.length}</span>
              </div>

              {cartes.length === 0 && (
                <div className="vide">Aucune commande</div>
              )}

              {cartes.map(commande => {
                const pct = progression(commande);
                const tousCoches = pct === 100;

                return (
                  <div className={`carte ${tousCoches ? 'carte-done' : ''}`} key={commande.id}>
                    {/* Top */}
                    <div className="carte-top">
                      <span className="ref-badge">#{commande.reference}</span>
                      <span className="carte-date">
                        {commande.date_livraison
                          ? `Livraison : ${commande.date_livraison}`
                          : new Date(commande.date_reception).toLocaleDateString('fr-FR')}
                      </span>
                    </div>

                    {/* Client */}
                    <div className="carte-client">{commande.client}</div>

                    {/* N° commande client */}
                    {commande.numero_commande && (
                      <div className="carte-num">Réf. client : {commande.numero_commande}</div>
                    )}

                    {/* Pièce jointe */}
                    {commande.pdf_nom && (
                      <div className="attach-row">
                        <span className="attach-info">📄 {commande.pdf_nom}</span>
                      </div>
                    )}

                    {/* Produits avec checkboxes */}
                    <div className="produits">
                      {commande.produits?.map(produit => (
                        <div className="produit-row" key={produit.id}>
                          <input
                            type="checkbox"
                            checked={produit.fait}
                            onChange={e => toggleProduit(produit.id, e.target.checked)}
                          />
                          <span className={`produit-nom ${produit.fait ? 'fait' : ''}`}>
                            {produit.nom}
                          </span>
                          <span className={`produit-qte ${produit.fait ? 'fait' : ''}`}>
                            ×{produit.quantite}
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* Barre de progression */}
                    <div className="prog-wrap">
                      <div className="prog-labels">
                        <span className="prog-txt">Progression</span>
                        <span className="prog-pct">{pct}%</span>
                      </div>
                      <div className="prog-bar">
                        <div
                          className="prog-fill"
                          style={{ width: `${pct}%`, background: statut.couleur }}
                        />
                      </div>
                    </div>

                    {/* Bandeau tous prêts */}
                    {tousCoches && (
                      <div className="all-done">✅ Tous les produits prêts !</div>
                    )}

                    {/* Bouton action */}
                    {action && (
                      <button
                        className={`action-btn ${statut.key === 'recu' ? 'btn-pink' : 'btn-outline'}`}
                        onClick={() => changerStatut(commande.reference, action.next)}
                      >
                        {action.label}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}