import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import './Historique.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Historique() {
  const [commandes, setCommandes]     = useState([]);
  const [chargement, setChargement]   = useState(true);
  const [recherche, setRecherche]     = useState('');
  const [activeId, setActiveId]       = useState(null);

  const chargerCommandes = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/commandes`);
      const livrees = res.data.filter(c => c.statut === 'livre');
      setCommandes(livrees);
    } catch (e) {
      toast.error('Impossible de charger l\'historique');
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    chargerCommandes();
    const interval = setInterval(chargerCommandes, 30000);
    return () => clearInterval(interval);
  }, [chargerCommandes]);

  const formatDate = (date) => {
    if (!date) return '—';
    return new Date(date).toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  };

  const formatCA = (montant) => {
    if (!montant) return '—';
    return new Intl.NumberFormat('fr-FR').format(montant) + ' MUR';
  };

  const commandesFiltrees = commandes.filter(c => {
    if (!recherche) return true;
    const q = recherche.toLowerCase();
    return (
      c.reference?.toLowerCase().includes(q) ||
      c.client?.toLowerCase().includes(q) ||
      c.numero_commande?.toLowerCase().includes(q)
    );
  });

  const caTotal = commandes.reduce((sum, c) => sum + (c.montant_total || 0), 0);

  if (chargement) return <div className="chargement">Chargement de l'historique...</div>;

  return (
    <div className="historique">
      <div className="hist-header">
        <div>
          <h2 className="hist-title">📜 Historique des livraisons</h2>
          <p className="hist-sub">{commandes.length} commande{commandes.length > 1 ? 's' : ''} livrée{commandes.length > 1 ? 's' : ''} — CA total : {formatCA(caTotal)}</p>
        </div>
      </div>

      <div className="hist-searchbar">
        <span>🔍</span>
        <input
          type="text"
          placeholder="Rechercher par référence, client…"
          value={recherche}
          onChange={e => setRecherche(e.target.value)}
        />
        {recherche && <button onClick={() => setRecherche('')}>✕</button>}
      </div>

      {commandesFiltrees.length === 0 ? (
        <div className="empty-hist">
          {recherche ? 'Aucune commande trouvée' : 'Aucune commande livrée pour l\'instant'}
        </div>
      ) : (
        <div className="hist-list">
          {commandesFiltrees.map(commande => (
            <div key={commande.id}>
              <div
                className={`hist-card ${activeId === commande.id ? 'active' : ''}`}
                onClick={() => setActiveId(activeId === commande.id ? null : commande.id)}
              >
                <div className="hist-card-left">
                  <span className="hist-ref">#{commande.reference}</span>
                  <span className="hist-client">{commande.client}</span>
                  {commande.numero_commande && (
                    <span className="hist-num">Réf. client : {commande.numero_commande}</span>
                  )}
                </div>
                <div className="hist-card-right">
                  {commande.montant_total && (
                    <span className="hist-ca">{formatCA(commande.montant_total)}</span>
                  )}
                  <span className="hist-date">{formatDate(commande.date_reception)}</span>
                  <span className="hist-badge">✅ Livré</span>
                </div>
              </div>

              {activeId === commande.id && (
                <div className="hist-detail">
                  <div className="hist-detail-header">
                    <div className="hist-detail-info">
                      {commande.date_livraison && <span>📅 Livraison prévue : {commande.date_livraison}</span>}
                      {commande.email_client && <span>✉️ {commande.email_client}</span>}
                      {commande.telephone_client && <span>📞 {commande.telephone_client}</span>}
                      {commande.pdf_nom && <span>📄 {commande.pdf_nom}</span>}
                    </div>
                  </div>
                  <table className="hist-produits">
                    <thead>
                      <tr>
                        <th>Produit</th>
                        <th>EAN</th>
                        <th>Quantité</th>
                      </tr>
                    </thead>
                    <tbody>
                      {commande.produits?.map(p => (
                        <tr key={p.id}>
                          <td>{p.nom}</td>
                          <td className="td-ean">{p.ean || '—'}</td>
                          <td>×{p.quantite}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
