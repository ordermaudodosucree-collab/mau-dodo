import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import './Stocks.css';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Stocks() {
  const [stocks, setStocks]             = useState([]);
  const [chargement, setChargement]     = useState(true);
  const [showAjouter, setShowAjouter]   = useState(false);
  const [mouvementId, setMouvementId]   = useState(null);
  const [mouvementType, setMouvementType] = useState('entree');
  const [recherche, setRecherche]       = useState('');

  const [formNom, setFormNom]           = useState('');
  const [formEan, setFormEan]           = useState('');
  const [formQte, setFormQte]           = useState(0);
  const [formSeuil, setFormSeuil]       = useState(50);

  const [mouvQte, setMouvQte]           = useState(0);
  const [mouvMotif, setMouvMotif]       = useState('');

  const chargerStocks = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/stocks`);
      setStocks(res.data);
    } catch (e) {
      toast.error('Impossible de charger les stocks');
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => { chargerStocks(); }, [chargerStocks]);

  const ajouterStock = async () => {
    if (!formNom.trim()) { toast.error('Le nom est obligatoire'); return; }
    try {
      await axios.post(`${API}/stocks`, {
        nom: formNom, ean: formEan || null,
        quantite: parseInt(formQte) || 0,
        seuil_alerte: parseInt(formSeuil) || 50
      });
      toast.success('Produit ajouté au stock !');
      setShowAjouter(false);
      setFormNom(''); setFormEan(''); setFormQte(0); setFormSeuil(50);
      chargerStocks();
    } catch (e) {
      toast.error('Erreur lors de l\'ajout');
    }
  };

  const faireMouvement = async () => {
    if (!mouvQte || mouvQte <= 0) { toast.error('Quantité invalide'); return; }
    try {
      await axios.post(`${API}/stocks/${mouvementId}/${mouvementType}`, {
        type: mouvementType,
        quantite: parseInt(mouvQte),
        motif: mouvMotif || null
      });
      toast.success(mouvementType === 'entree' ? 'Stock ajouté !' : 'Stock déduit !');
      setMouvementId(null); setMouvQte(0); setMouvMotif('');
      chargerStocks();
    } catch (e) {
      toast.error('Erreur lors du mouvement');
    }
  };

  const majSeuil = async (stockId, seuil) => {
    try {
      await axios.patch(`${API}/stocks/${stockId}`, { seuil_alerte: parseInt(seuil) });
      chargerStocks();
    } catch (e) {
      toast.error('Erreur mise à jour seuil');
    }
  };

  const stocksFiltres = stocks.filter(s =>
    !recherche || s.nom.toLowerCase().includes(recherche.toLowerCase()) ||
    (s.ean && s.ean.includes(recherche))
  );

  const enAlerte = stocks.filter(s => s.quantite <= s.seuil_alerte).length;

  if (chargement) return <div className="chargement">Chargement des stocks...</div>;

  return (
    <div className="stocks-page">
      <div className="stocks-header">
        <div>
          <h2 className="stocks-title">📦 Gestion des stocks</h2>
          {enAlerte > 0 && (
            <div className="alerte-banner">
              ⚠️ {enAlerte} produit{enAlerte > 1 ? 's' : ''} en alerte de stock !
            </div>
          )}
        </div>
        <button className="btn-ajouter" onClick={() => setShowAjouter(true)}>
          + Ajouter un produit
        </button>
      </div>

      <div className="stocks-searchbar">
        <span>🔍</span>
        <input
          type="text"
          placeholder="Rechercher par nom ou EAN…"
          value={recherche}
          onChange={e => setRecherche(e.target.value)}
        />
        {recherche && <button onClick={() => setRecherche('')}>✕</button>}
      </div>

      {/* FORMULAIRE AJOUT */}
      {showAjouter && (
        <div className="form-card">
          <h3 className="form-title">Nouveau produit en stock</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Nom du produit *</label>
              <input type="text" value={formNom} onChange={e => setFormNom(e.target.value)}
                placeholder="ex: Pate de Fruit Ananas 200G" />
            </div>
            <div className="form-group">
              <label>EAN (code-barres)</label>
              <input type="text" value={formEan} onChange={e => setFormEan(e.target.value)}
                placeholder="ex: 6091314110176" />
            </div>
            <div className="form-group">
              <label>Quantité initiale</label>
              <input type="number" value={formQte} onChange={e => setFormQte(e.target.value)} min="0" />
            </div>
            <div className="form-group">
              <label>Seuil d'alerte</label>
              <input type="number" value={formSeuil} onChange={e => setFormSeuil(e.target.value)} min="0" />
            </div>
          </div>
          <div className="form-actions">
            <button className="btn-save" onClick={ajouterStock}>Enregistrer</button>
            <button className="btn-cancel" onClick={() => setShowAjouter(false)}>Annuler</button>
          </div>
        </div>
      )}

      {/* FORMULAIRE MOUVEMENT */}
      {mouvementId && (
        <div className="form-card">
          <h3 className="form-title">
            {mouvementType === 'entree' ? '➕ Entrée de stock' : '➖ Sortie de stock'}
          </h3>
          <div className="mouv-type-selector">
            <button
              className={`mouv-btn ${mouvementType === 'entree' ? 'active-entree' : ''}`}
              onClick={() => setMouvementType('entree')}
            >➕ Entrée</button>
            <button
              className={`mouv-btn ${mouvementType === 'sortie' ? 'active-sortie' : ''}`}
              onClick={() => setMouvementType('sortie')}
            >➖ Sortie</button>
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label>Quantité</label>
              <input type="number" value={mouvQte} onChange={e => setMouvQte(e.target.value)} min="1" />
            </div>
            <div className="form-group">
              <label>Motif (optionnel)</label>
              <input type="text" value={mouvMotif} onChange={e => setMouvMotif(e.target.value)}
                placeholder="ex: ajout manuel, retour client..." />
            </div>
          </div>
          <div className="form-actions">
            <button className="btn-save" onClick={faireMouvement}>Confirmer</button>
            <button className="btn-cancel" onClick={() => { setMouvementId(null); setMouvQte(0); setMouvMotif(''); }}>Annuler</button>
          </div>
        </div>
      )}

      {/* TABLEAU STOCKS */}
      {stocksFiltres.length === 0 ? (
        <div className="empty-stocks">
          {recherche ? 'Aucun produit trouvé' : 'Aucun produit en stock — cliquez sur "+ Ajouter un produit"'}
        </div>
      ) : (
        <div className="stocks-table-wrap">
          <table className="stocks-table">
            <thead>
              <tr>
                <th>Produit</th>
                <th>EAN</th>
                <th>Stock actuel</th>
                <th>Seuil alerte</th>
                <th>Statut</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {stocksFiltres.map(stock => {
                const enAlerte = stock.quantite <= stock.seuil_alerte;
                return (
                  <tr key={stock.id} className={enAlerte ? 'row-alerte' : ''}>
                    <td className="td-nom">{stock.nom}</td>
                    <td className="td-ean">{stock.ean || '—'}</td>
                    <td className="td-qte">
                      <span className={`qte-badge ${enAlerte ? 'rouge' : 'vert'}`}>
                        {stock.quantite}
                      </span>
                    </td>
                    <td className="td-seuil">
                      <input
                        type="number"
                        className="seuil-input"
                        defaultValue={stock.seuil_alerte}
                        min="0"
                        onBlur={e => majSeuil(stock.id, e.target.value)}
                      />
                    </td>
                    <td>
                      {enAlerte
                        ? <span className="statut-badge rouge">⚠️ Alerte</span>
                        : <span className="statut-badge vert">✅ OK</span>
                      }
                    </td>
                    <td className="td-actions">
                      <button className="btn-entree" onClick={() => { setMouvementId(stock.id); setMouvementType('entree'); }}>
                        ➕ Entrée
                      </button>
                      <button className="btn-sortie" onClick={() => { setMouvementId(stock.id); setMouvementType('sortie'); }}>
                        ➖ Sortie
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
