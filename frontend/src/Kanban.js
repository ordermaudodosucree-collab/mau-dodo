import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import logo from './logo.png';
import './Kanban.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const STATUTS = [
  { key: 'recu',       label: 'Commande reçue',  classe: 'col-recu',  badge: 'b-brun',  couleur: '#5C3317' },
  { key: 'production', label: 'En production',    classe: 'col-prod',  badge: 'b-vert',  couleur: '#639922' },
  { key: 'livraison',  label: 'En livraison',     classe: 'col-livr',  badge: 'b-bleu',  couleur: '#1A5FAD' },
];

export default function Kanban() {
  const [commandes, setCommandes]       = useState([]);
  const [recherche, setRecherche]       = useState('');
  const [chargement, setChargement]     = useState(true);
  const [commandeActive, setCommandeActive] = useState(null);

  const chargerCommandes = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/commandes`);
      setCommandes(res.data);
      if (commandeActive) {
        const updated = res.data.find(c => c.id === commandeActive.id);
        if (updated) setCommandeActive(updated);
      }
    } catch (e) {
      toast.error('Impossible de charger les commandes');
    } finally {
      setChargement(false);
    }
  }, [commandeActive]);

  useEffect(() => { chargerCommandes(); }, [chargerCommandes]);

  useEffect(() => {
    const wsUrl = API.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/ws`);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'nouvelle_commande') toast.success(`Nouvelle commande : ${msg.reference} !`);
      chargerCommandes();
    };
    return () => ws.close();
  }, [chargerCommandes]);

  const changerStatut = async (reference, nouveauStatut) => {
    try {
      await axios.patch(`${API}/commandes/${reference}/statut`, { statut: nouveauStatut });
      toast.success('Statut mis à jour !');
      setCommandeActive(null);
      chargerCommandes();
    } catch (e) {
      toast.error('Erreur lors du changement de statut');
    }
  };

  const toggleProduit = async (produitId, fait) => {
    try {
      await axios.patch(`${API}/produits/${produitId}`, { fait });
      chargerCommandes();
    } catch (e) {
      toast.error('Erreur mise à jour produit');
    }
  };

  const commandesFiltrees = commandes.filter(c => {
    if (!recherche) return true;
    const q = recherche.toLowerCase();
    return (
      c.reference?.toLowerCase().includes(q) ||
      c.client?.toLowerCase().includes(q) ||
      c.numero_commande?.toLowerCase().includes(q) ||
      c.produits?.some(p => p.nom?.toLowerCase().includes(q) || p.ean?.includes(q))
    );
  });

  const commandesDuStatut = (statut) => commandesFiltrees.filter(c => c.statut === statut);

  const progression = (commande) => {
    if (!commande.produits?.length) return 0;
    const faits = commande.produits.filter(p => p.fait).length;
    return Math.round((faits / commande.produits.length) * 100);
  };

  const prochainStatut = (statut) => {
    if (statut === 'recu')       return { label: 'Démarrer production ↗', next: 'production' };
    if (statut === 'production') return { label: 'Envoyer en livraison ↗', next: 'livraison' };
    if (statut === 'livraison')  return { label: 'Confirmer réception ↗', next: 'livre' };
    return null;
  };

  const statutInfo = (key) => STATUTS.find(s => s.key === key);

  if (chargement) return <div className="chargement">Chargement des commandes...</div>;

  return (
    <div className="kanban">
      {/* HEADER */}
      <div className="header">
        <div className="logo-wrap">
          <img src={logo} alt="Mau Dodo Sucrée" className="logo-img" />
          <div className="logo-text">
            <div className="logo-name">Mau Dodo Sucrée</div>
            <div className="logo-sub">Suivi des commandes</div>
          </div>
        </div>
        <div className="header-right">
          <div className="stat-pill"><b>{commandes.length}</b> commandes</div>
          <div className="stat-pill"><b>{new Date().toLocaleDateString('fr-FR')}</b></div>
        </div>
      </div>

      {/* RECHERCHE */}
      <div className="searchbar">
        <span>🔍</span>
        <input
          type="text"
          placeholder="Rechercher par référence, client, produit ou EAN…"
          value={recherche}
          onChange={e => setRecherche(e.target.value)}
        />
        {recherche && <button className="clear-btn" onClick={() => setRecherche('')}>✕</button>}
      </div>

      {/* COLONNES HORIZONTALES */}
      <div className="colonnes">
        {STATUTS.map(statut => {
          const cartes = commandesDuStatut(statut.key);
          return (
            <div className={`colonne ${statut.classe}`} key={statut.key}>
              <div className="col-header">
                <span className="col-titre">{statut.label}</span>
                <span className={`badge ${statut.badge}`}>{cartes.length}</span>
              </div>
              {cartes.length === 0 && <div className="vide">Aucune commande</div>}
              {cartes.map(commande => {
                const pct = progression(commande);
                return (
                  <div
                    className={`carte ${pct === 100 ? 'carte-done' : ''}`}
                    key={commande.id}
                    onClick={() => setCommandeActive(commande)}
                  >
                    <div className="carte-top">
                      <span className="ref-badge">#{commande.reference}</span>
                      <span className="carte-date">
                        {commande.date_livraison ? `📅 ${commande.date_livraison}` : new Date(commande.date_reception).toLocaleDateString('fr-FR')}
                      </span>
                    </div>
                    <div className="carte-client">{commande.client}</div>
                    {commande.numero_commande && <div className="carte-num">Réf. : {commande.numero_commande}</div>}
                    <div className="prog-wrap">
                      <div className="prog-labels">
                        <span className="prog-txt">{commande.produits?.length || 0} produits</span>
                        <span className="prog-pct">{pct}%</span>
                      </div>
                      <div className="prog-bar">
                        <div className="prog-fill" style={{ width: `${pct}%`, background: statut.couleur }} />
                      </div>
                    </div>
                    {pct === 100 && <div className="all-done-mini">✅ Prêt !</div>}
                    <div className="carte-hint">Cliquer pour voir les détails →</div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* MODAL — DÉTAIL COMMANDE */}
      {commandeActive && (
        <div className="modal-overlay" onClick={() => setCommandeActive(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <div className="modal-ref">#{commandeActive.reference}</div>
                <div className="modal-client">{commandeActive.client}</div>
                {commandeActive.numero_commande && (
                  <div className="modal-num">Réf. client : {commandeActive.numero_commande}</div>
                )}
              </div>
              <button className="modal-close" onClick={() => setCommandeActive(null)}>✕</button>
            </div>

            <div className="modal-infos">
              {commandeActive.date_livraison && (
                <div className="modal-info-pill">📅 Livraison : {commandeActive.date_livraison}</div>
              )}
              {commandeActive.email_client && (
                <div className="modal-info-pill">✉️ {commandeActive.email_client}</div>
              )}
              {commandeActive.telephone_client && (
                <div className="modal-info-pill">📞 {commandeActive.telephone_client}</div>
              )}
              {commandeActive.pdf_nom && (
                <div className="modal-info-pill">📄 {commandeActive.pdf_nom}</div>
              )}
            </div>

            {/* PRODUITS */}
            <div className="modal-produits">
              <div className="produit-header">
                <span></span>
                <span>Produit</span>
                <span>EAN</span>
                <span>Qté</span>
              </div>
              {commandeActive.produits?.map(produit => (
                <div className="produit-row" key={produit.id}>
                  <input
                    type="checkbox"
                    checked={produit.fait}
                    onChange={e => toggleProduit(produit.id, e.target.checked)}
                  />
                  <span className={`produit-nom ${produit.fait ? 'fait' : ''}`}>{produit.nom}</span>
                  <span className={`produit-ean ${produit.fait ? 'fait' : ''}`}>{produit.ean || '—'}</span>
                  <span className={`produit-qte ${produit.fait ? 'fait' : ''}`}>×{produit.quantite}</span>
                </div>
              ))}
            </div>

            {/* PROGRESSION */}
            <div className="prog-wrap" style={{marginTop: '1rem'}}>
              <div className="prog-labels">
                <span className="prog-txt">Progression</span>
                <span className="prog-pct">{progression(commandeActive)}%</span>
              </div>
              <div className="prog-bar">
                <div className="prog-fill" style={{
                  width: `${progression(commandeActive)}%`,
                  background: statutInfo(commandeActive.statut)?.couleur || '#5C3317'
                }} />
              </div>
            </div>

            {progression(commandeActive) === 100 && (
              <div className="all-done">✅ Tous les produits prêts !</div>
            )}

            {/* BOUTON ACTION */}
            {prochainStatut(commandeActive.statut) && (
              <button
                className={`action-btn ${commandeActive.statut === 'recu' ? 'btn-brun' : 'btn-outline'}`}
                onClick={() => changerStatut(commandeActive.reference, prochainStatut(commandeActive.statut).next)}
              >
                {prochainStatut(commandeActive.statut).label}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}