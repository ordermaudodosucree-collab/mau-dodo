import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import './Kanban.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const STATUTS = [
  { key: 'recu',       label: 'Commande reçue',  classe: 'col-recu',  badge: 'b-brun',  couleur: '#5C3317' },
  { key: 'production', label: 'En production',    classe: 'col-prod',  badge: 'b-vert',  couleur: '#639922' },
  { key: 'livraison',  label: 'En livraison',     classe: 'col-livr',  badge: 'b-bleu',  couleur: '#1A5FAD' },
];

export default function Kanban() {
  const [commandes, setCommandes]           = useState([]);
  const [recherche, setRecherche]           = useState('');
  const [chargement, setChargement]         = useState(true);
  const [activeId, setActiveId]             = useState(null);
  const intervalRef                         = useRef(null);

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
    intervalRef.current = setInterval(chargerCommandes, 30000);
    return () => clearInterval(intervalRef.current);
  }, [chargerCommandes]);

  const fermer = (e) => {
    if (e) e.stopPropagation();
    setActiveId(null);
  };

  const ouvrirCarte = (id) => {
    setActiveId(prev => prev === id ? null : id);
  };

  const changerStatut = async (reference, nouveauStatut) => {
    try {
      await axios.patch(`${API}/commandes/${reference}/statut`, { statut: nouveauStatut });
      toast.success('Statut mis à jour !');
      setActiveId(null);
      await chargerCommandes();
    } catch (e) {
      toast.error('Erreur lors du changement de statut');
    }
  };

  const toggleProduit = async (e, produitId, fait) => {
    e.stopPropagation();
    try {
      await axios.patch(`${API}/produits/${produitId}`, { fait });
      await chargerCommandes();
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
  const commandeActive = commandes.find(c => c.id === activeId) || null;

  const dateLivraisonPrevue = (dateReception) => {
  if (!dateReception) return '—';
  const date = new Date(dateReception);
  date.setDate(date.getDate() + 4);
  return date.toLocaleDateString('fr-FR');
};

if (chargement) return <div className="chargement">Chargement des commandes...</div>;


  return (
    <div className="kanban">


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
                const isActive = activeId === commande.id;
                return (
                  <div
                    className={`carte ${pct === 100 ? 'carte-done' : ''} ${isActive ? 'carte-active' : ''}`}
                    key={commande.id}
                    onClick={() => ouvrirCarte(commande.id)}
                  >
                    <div className="carte-top">
  <span className="ref-badge">#{commande.reference}</span>
  <span className="carte-date">
    📅 {commande.date_livraison || dateLivraisonPrevue(commande.date_reception)}
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
                    <div className="carte-hint">{isActive ? '▲ Fermer' : '▼ Voir détails'}</div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {commandeActive && (
        <div className="detail-panel">
          <div className="panel-header">
            <div>
              <div className="panel-ref">#{commandeActive.reference}</div>
              <div className="panel-client">{commandeActive.client}</div>
              {commandeActive.numero_commande && (
                <div className="panel-num">Réf. client : {commandeActive.numero_commande}</div>
              )}
            </div>
            <button className="panel-close" onClick={fermer}>Fermer ✕</button>
          </div>

          <div className="panel-infos">
<div className="panel-info-pill">📅 Livraison prévue : {commandeActive.date_livraison || dateLivraisonPrevue(commandeActive.date_reception)}</div>            {commandeActive.email_client && <div className="panel-info-pill">✉️ {commandeActive.email_client}</div>}
            {commandeActive.telephone_client && <div className="panel-info-pill">📞 {commandeActive.telephone_client}</div>}
            {commandeActive.pdf_nom && <div className="panel-info-pill">📄 {commandeActive.pdf_nom}</div>}
          </div>

          <div className="produits">
            <div className="produit-header">
              <span></span><span>Produit</span><span>EAN</span><span>Qté</span>
            </div>
            {commandeActive.produits?.map(produit => (
              <div className="produit-row" key={produit.id}>
                <input
                  type="checkbox"
                  checked={produit.fait}
                  onChange={e => toggleProduit(e, produit.id, e.target.checked)}
                />
                <span className={`produit-nom ${produit.fait ? 'fait' : ''}`}>{produit.nom}</span>
                <span className={`produit-ean ${produit.fait ? 'fait' : ''}`}>{produit.ean || '—'}</span>
                <span className={`produit-qte ${produit.fait ? 'fait' : ''}`}>×{produit.quantite}</span>
              </div>
            ))}
          </div>

          <div className="prog-wrap">
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

          {prochainStatut(commandeActive.statut) && (
            <button
              className={`action-btn ${commandeActive.statut === 'recu' ? 'btn-brun' : 'btn-outline'}`}
              onClick={() => changerStatut(commandeActive.reference, prochainStatut(commandeActive.statut).next)}
            >
              {prochainStatut(commandeActive.statut).label}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
