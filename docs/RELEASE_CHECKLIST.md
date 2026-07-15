# Checklist avant passage en public

À vérifier **avant** de rendre le dépôt `audiomnesis` public :

- [ ] `docs/bilan-cr.docx` : le modèle contient l'en-tête Aloïs (adresse, ADELI/RPPS,
      téléphone, liste de l'équipe, SIRET). Décider : le remplacer par un modèle
      générique/anonymisé, ou l'assumer (ces informations sont par ailleurs publiques
      sur le site de l'association).
- [ ] Vérifier qu'aucun `bilan-cr_completed.docx` / `bilan-cr_example.docx` n'est
      tracké : `git ls-files docs/` ne doit lister que `bilan-cr.docx` et les .md.
- [ ] Vérifier l'historique : `git log --all --name-only | grep -i completed` → vide.
- [ ] `recordings/` et sorties `CR_*.docx` / `*_transcript.txt` : jamais dans le dépôt
      (déjà gitignorés — ne pas forcer avec `git add -f`).
- [ ] Relire `docs/superpowers/specs` et `plans` : pas de données personnelles
      (ils décrivent l'outil, pas des patients — normalement OK).
- [ ] Ajouter une licence (MIT ? — décision à prendre).
- [ ] README : mentionner que l'outil est une aide à la rédaction et que le clinicien
      reste responsable du contenu ; consentement du patient requis pour
      l'enregistrement (RGPD).
