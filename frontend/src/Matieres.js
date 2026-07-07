import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';


const API = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function MatieresPremières() {
  const [matieres, setMatieres]         = useState([]);
  const [recettes, setRecettes]         = useState([]);
  const [chargement, setChargement]     = useState(true);
  const [onglet, setOnglet]             = useState('matieres'); // 'matieres' | 'recettes'
  const [showAjouter, setShowAjouter]   = useState(false);
  const [showRecette, setShowRecette]   = useState(false);

  // Formulaire matière première
  const [formNom, setFormNom]           = useState('');
  const [formUnite, setFormUnite]       = useState('g');
  const [formStock, setFormStock]       = useState(0);
  const [formSeuil, setFormSeuil]       = useState(0);

  // Formulaire recette
  const [recetteNom, setRecetteNom]     = useState('');
  const [recetteGrammage, setRecetteGrammage] = useState(200);
  const [recetteIngredients, setRecetteIngredients] = useState([]);

  const charger = useCallback(async () => {
    try {
      const [mp, rec] = await Promise.all([
        axios.get(`${API}/matieres-premieres`),
        axios.get(`${API}/recettes`)
      ]);
      setMatieres(mp.data);
      setRecettes(rec.data);
    } catch (e) {
      toast.error('Impossible de charger les données');
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => { charger(); }, [charger]);

  const ajouterMatiere = async () => {
    if (!formNom.trim()) { toast.error('Nom obligatoire'); return; }
    try {
      await axios.post(`${API}/matieres-premieres`, {
        nom: formNom, unite: formUnite,
        stock: parseInt(formStock) || 0,
        seuil_alerte: parseInt(formSeuil) || 0
      });
      toast.success('Matière première ajoutée !');
      setShowAjouter(false);
      setFormNom(''); setFormUnite('g'); setFormStock(0); setFormSeuil(0);
      charger();
    } catch (e) {
      toast.error('Erreur lors de l\'ajout');
    }
  };

  const majStock = async (id, stock) => {
    try {
      await axios.patch(`${API}/matieres-premieres/${id}`, { stock: parseInt(stock) });
      charger();
    } catch (e) {
      toast.error('Erreur mise à jour stock');
    }
  };

  const ajouterIngredient = () => {
    setRecetteIngredients([...recetteIngredients, { matiere_premiere_id: '', quantite: 0 }]);
  };

  const majIngredient = (index, field, value) => {
    const updated = [...recetteIngredients];
    updated[index][field] = value;
    setRecetteIngredients(updated);
  };

  const supprimerIngredient = (index) => {
    setRecetteIngredients(recetteIngredients.filter((_, i) => i !== index));
  };

  const creerRecette = async () => {
    if (!recetteNom.trim()) { toast.error('Nom du produit obligatoire'); return; }
    if (recetteIngredients.length === 0) { toast.error('Ajouter au moins un ingrédient'); return; }
    try {
      await axios.post(`${API}/recettes`, {
        produit_nom: recetteNom,
        grammage: parseInt(recetteGrammage),
        ingredients: recetteIngredients.map(i => ({
          matiere_premiere_id: parseInt(i.matiere_premiere_id),
          quantite: parseInt(i.quantite)
        }))
      });
      toast.success('Recette créée !');
      setShowRecette(false);
      setRecetteNom(''); setRecetteGrammage(200); setRecetteIngredients([]);
      charger();
    } catch (e) {
      toast.error('Erreur création recette');
    }
  };

  if (chargement) return <div className="chargement">Chargement...</div>;

  return (
    <div className="mp-page">
      <div className="mp-header">
        <h2 className="mp-title">🧪 Matières Premières & Recettes</h2>
        <div className="mp-actions">
          {onglet === 'matieres' && (
            <button className="btn-ajouter" onClick={() => setShowAjouter(true)}>
              + Ajouter matière première
            </button>
          )}
          {onglet === 'recettes' && (
            <button className="btn-ajouter" onClick={() => setShowRecette(true)}>
              + Créer une recette
            </button>
          )}
        </div>
      </div>

      {/* ONGLETS */}
      <div className="mp-onglets">
        <button className={`onglet-btn ${onglet === 'matieres' ? 'active' : ''}`}
          onClick={() => setOnglet('matieres')}>
          🧂 Matières premières ({matieres.length})
        </button>
        <button className={`onglet-btn ${onglet === 'recettes' ? 'active' : ''}`}
          onClick={() => setOnglet('recettes')}>
          📋 Recettes ({recettes.length})
        </button>
      </div>

      {/* FORMULAIRE MATIERE PREMIERE */}
      {showAjouter && onglet === 'matieres' && (
        <div className="form-card">
          <h3 className="form-title">Nouvelle matière première</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Nom *</label>
              <input type="text" value={formNom} onChange={e => setFormNom(e.target.value)}
                placeholder="ex: Sucre" />
            </div>
            <div className="form-group">
              <label>Unité *</label>
              <select value={formUnite} onChange={e => setFormUnite(e.target.value)}>
                <option value="g">g (grammes)</option>
                <option value="kg">kg (kilogrammes)</option>
                <option value="ml">ml (millilitres)</option>
                <option value="l">l (litres)</option>
              </select>
            </div>
            <div className="form-group">
              <label>Stock initial</label>
              <input type="number" value={formStock} onChange={e => setFormStock(e.target.value)} min="0" />
            </div>
            <div className="form-group">
              <label>Seuil d'alerte</label>
              <input type="number" value={formSeuil} onChange={e => setFormSeuil(e.target.value)} min="0" />
            </div>
          </div>
          <div className="form-actions">
            <button className="btn-save" onClick={ajouterMatiere}>Enregistrer</button>
            <button className="btn-cancel" onClick={() => setShowAjouter(false)}>Annuler</button>
          </div>
        </div>
      )}

      {/* FORMULAIRE RECETTE */}
      {showRecette && onglet === 'recettes' && (
        <div className="form-card">
          <h3 className="form-title">Nouvelle recette</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Nom du produit fini *</label>
              <input type="text" value={recetteNom} onChange={e => setRecetteNom(e.target.value)}
                placeholder="ex: MDS PATE DE FRUITS MANGO" />
            </div>
            <div className="form-group">
              <label>Grammage</label>
              <select value={recetteGrammage} onChange={e => setRecetteGrammage(e.target.value)}>
                <option value="100">100g</option>
                <option value="200">200g</option>
              </select>
            </div>
          </div>

          <h4 className="ingredients-titre">Ingrédients pour 1 unité</h4>
          {recetteIngredients.map((ing, index) => (
            <div className="ingredient-row" key={index}>
              <select value={ing.matiere_premiere_id}
                onChange={e => majIngredient(index, 'matiere_premiere_id', e.target.value)}>
                <option value="">Choisir matière première</option>
                {matieres.map(mp => (
                  <option key={mp.id} value={mp.id}>{mp.nom} ({mp.unite})</option>
                ))}
              </select>
              <input type="number" value={ing.quantite} min="0"
                onChange={e => majIngredient(index, 'quantite', e.target.value)}
                placeholder="Quantité" />
              <button className="btn-supprimer" onClick={() => supprimerIngredient(index)}>✕</button>
            </div>
          ))}
          <button className="btn-add-ingredient" onClick={ajouterIngredient}>
            + Ajouter un ingrédient
          </button>

          <div className="form-actions" style={{marginTop: '1rem'}}>
            <button className="btn-save" onClick={creerRecette}>Créer la recette</button>
            <button className="btn-cancel" onClick={() => setShowRecette(false)}>Annuler</button>
          </div>
        </div>
      )}

      {/* LISTE MATIERES PREMIERES */}
      {onglet === 'matieres' && (
        <div className="mp-table-wrap">
          {matieres.length === 0 ? (
            <div className="empty">Aucune matière première — cliquez sur "+ Ajouter"</div>
          ) : (
            <table className="mp-table">
              <thead>
                <tr>
                  <th>Matière première</th>
                  <th>Unité</th>
                  <th>Stock actuel</th>
                  <th>Seuil alerte</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {matieres.map(mp => {
                  const enAlerte = mp.stock <= mp.seuil_alerte;
                  return (
                    <tr key={mp.id} className={enAlerte ? 'row-alerte' : ''}>
                      <td className="td-nom">{mp.nom}</td>
                      <td>{mp.unite}</td>
                      <td>
                        <input type="number" className="stock-input"
                          defaultValue={mp.stock} min="0"
                          onBlur={e => majStock(mp.id, e.target.value)} />
                      </td>
                      <td>{mp.seuil_alerte}</td>
                      <td>
                        {enAlerte
                          ? <span className="statut-badge rouge">⚠️ Alerte</span>
                          : <span className="statut-badge vert">✅ OK</span>
                        }
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* LISTE RECETTES */}
      {onglet === 'recettes' && (
        <div className="recettes-list">
          {recettes.length === 0 ? (
            <div className="empty">Aucune recette — cliquez sur "+ Créer une recette"</div>
          ) : (
            recettes.map(recette => (
              <div className="recette-card" key={recette.id}>
                <div className="recette-header">
                  <div>
                    <div className="recette-nom">{recette.produit_nom}</div>
                    <div className="recette-grammage">Recette pour 1 unité de {recette.grammage}g</div>
                  </div>
                </div>
                <table className="recette-table">
                  <thead>
                    <tr>
                      <th>Matière première</th>
                      <th>Quantité par unité</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recette.ingredients?.map(ing => (
                      <tr key={ing.id}>
                        <td>{ing.matiere_premiere?.nom || '—'}</td>
                        <td>{ing.quantite} {ing.matiere_premiere?.unite}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
