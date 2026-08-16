let generationOuverte = null;
let derniereURLDictionnaire = "/";
let utilisateurActuel = null;

function urlDictionnaire(mot, idGeneration = null) {
    let url = `/dictionnaire/${encodeURIComponent(mot)}`;

    if (idGeneration !== null && idGeneration !== undefined) {
        url += `/${encodeURIComponent(idGeneration)}`;
    }

    return url;
}

function afficherMessageCompte(message, type = "") {
    const element = document.getElementById("message_compte");
/opyio
    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = "message-compte";

    if (type) {
        element.classList.add(type);
    }
}

function memoriserURLDictionnaire() {
    const chemin = window.location.pathname;

    if (
        chemin !== "/compte" &&
        !chemin.startsWith("/utilisateur/")
    ) {
        derniereURLDictionnaire = chemin + window.location.search;
    }
}

function afficherEtatCompte() {
    const zoneDeconnecte = document.getElementById("compte_deconnecte");
    const zoneConnecte = document.getElementById("compte_connecte");
    const nomCompte = document.getElementById("nom_compte");

    if (!zoneDeconnecte || !zoneConnecte || !nomCompte) {
        return;
    }

    if (utilisateurActuel) {
        zoneDeconnecte.classList.add("cache");
        zoneConnecte.classList.remove("cache");
        nomCompte.textContent = utilisateurActuel.nom_utilisateur;
    } else {
        zoneDeconnecte.classList.remove("cache");
        zoneConnecte.classList.add("cache");
        nomCompte.textContent = "";
    }
}

async function chargerCompte() {
    try {
        const reponse = await fetch("/moi");
        const donnees = await reponse.json();

        if (donnees.connecte) {
            utilisateurActuel = donnees.utilisateur;
        } else {
            utilisateurActuel = null;
        }

        afficherEtatCompte();

    } catch (erreur) {
        console.error(erreur);
        utilisateurActuel = null;
        afficherEtatCompte();
    }
}

function changerModeCompte(mode) {
    const formConnexion = document.getElementById("form_connexion");
    const formInscription = document.getElementById("form_inscription");
    const ongletConnexion = document.getElementById("onglet_connexion");
    const ongletInscription = document.getElementById("onglet_inscription");

    if (mode === "inscription") {
        formConnexion.classList.add("cache");
        formInscription.classList.remove("cache");

        ongletConnexion.classList.remove("actif");
        ongletInscription.classList.add("actif");
    } else {
        formConnexion.classList.remove("cache");
        formInscription.classList.add("cache");

        ongletConnexion.classList.add("actif");
        ongletInscription.classList.remove("actif");
    }

    afficherMessageCompte("");
}

async function traiterReponseCompte(reponse) {
    const donnees = await reponse.json();

    if (donnees.erreur) {
        afficherMessageCompte(donnees.message || "Erreur.", "erreur");
        return;
    }

    utilisateurActuel = donnees.utilisateur;
    afficherEtatCompte();
    afficherMessageCompte("");

    if (generationOuverte?.id) {
        await ouvrirGeneration(generationOuverte.id);
    }
}

async function connexionCompte() {
    const identifiant = document.getElementById("compte_connexion_identifiant").value.trim();
    const motDePasse = document.getElementById("compte_connexion_mdp").value;

    if (!identifiant || !motDePasse) {
        afficherMessageCompte("Pseudo/e-mail et mot de passe nécessaires.", "erreur");
        return;
    }

    try {
        const reponse = await fetch("/connexion", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                nom_utilisateur: identifiant,
                mot_de_passe: motDePasse
            })
        });

        await traiterReponseCompte(reponse);

    } catch (erreur) {
        console.error(erreur);
        afficherMessageCompte("Impossible de contacter le serveur.", "erreur");
    }
}

async function inscriptionCompte() {
    const nom = document.getElementById("compte_inscription_nom").value.trim();
    const email = document.getElementById("compte_inscription_email").value.trim();
    const motDePasse = document.getElementById("compte_inscription_mdp").value;

    if (!nom || !email || !motDePasse) {
        afficherMessageCompte("Pseudo, e-mail et mot de passe nécessaires.", "erreur");
        return;
    }

    try {
        const reponse = await fetch("/inscription", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                nom_utilisateur: nom,
                email: email,
                mot_de_passe: motDePasse
            })
        });

        await traiterReponseCompte(reponse);

    } catch (erreur) {
        console.error(erreur);
        afficherMessageCompte("Impossible de contacter le serveur.", "erreur");
    }
}

async function chargerDepuisURL() {
    const chemin = decodeURIComponent(window.location.pathname);

    if (chemin === "/" || chemin.trim() === "") {
        return;
    }

    if (chemin === "/compte") {
        await chargerCompte();

        if (utilisateurActuel) {
            await ouvrirCompte();
        } else {
            afficherErreur("Tu dois être connecté pour accéder à ton compte.");
            history.replaceState(null, "", "/");
        }

        return;
    }

    if (chemin.startsWith("/utilisateur/")) {
        const morceaux = chemin
            .split("/")
            .map(morceau => morceau.trim())
            .filter(Boolean);

        const idProfil = morceaux[1];

        if (idProfil) {
            await ouvrirProfilUtilisateur(encodeURIComponent(idProfil));
        }

        return;
    }

    if (chemin.startsWith("/dictionnaire/")) {
        const morceaux = chemin
            .split("/")
            .map(morceau => morceau.trim())
            .filter(Boolean);

        // Pour /dictionnaire/édredon :
        // morceaux[0] = "dictionnaire"
        // morceaux[1] = "édredon"
        // morceaux[2] = id éventuel de génération

        const mot = morceaux[1];
        const idGeneration = morceaux[2] ? Number(morceaux[2]) : null;

        if (!mot) {
            return;
        }

        document.getElementById("mot").value = mot;

        await chargerGenerations(mot);
        await chargerSourcesBrutes(mot);

        if (idGeneration) {
            await ouvrirGeneration(idGeneration);
        } else {
            afficherMessage(`Page du mot « ${mot} » ouverte.`);
        }

        return;
    }

    afficherErreur("Page inconnue.");
}

async function deconnexionCompte() {
    try {
        await fetch("/deconnexion", {
            method: "POST"
        });

        utilisateurActuel = null;
        afficherEtatCompte();
        if (generationOuverte?.id) {
            await ouvrirGeneration(generationOuverte.id);
        }

    } catch (erreur) {
        console.error(erreur);
    }
}

const groupesSources = {
    wiktionary: {
        label: "Wiktionary",
        parentId: "source_wiktionary",
        enfantsName: "wiktionary_langues"
    },
    academie_fr: {
        label: "Académie française",
        parentId: "source_academie_fr",
        enfantsName: "academie_fr_editions"
    }
};

function basculerGroupeSource(cle) {
    const groupe = groupesSources[cle];
    const parent = document.getElementById(groupe.parentId);
    const enfants = document.querySelectorAll(`input[name="${groupe.enfantsName}"]`);

    parent.indeterminate = false;

    enfants.forEach(enfant => {
        enfant.checked = parent.checked;
    });
}

function mettreAJourParentSource(cle) {
    const groupe = groupesSources[cle];
    const parent = document.getElementById(groupe.parentId);
    const enfants = Array.from(document.querySelectorAll(`input[name="${groupe.enfantsName}"]`));

    const coches = enfants.filter(enfant => enfant.checked).length;

    if (coches === 0) {
        parent.checked = false;
        parent.indeterminate = false;
    } else if (coches === enfants.length) {
        parent.checked = true;
        parent.indeterminate = false;
    } else {
        parent.checked = false;
        parent.indeterminate = true;
    }
}

function creerCasesEnfants(nom, valeurs, cle) {
    return valeurs.map(valeur => `
        <label class="sous-source">
            <input type="checkbox"
                name="${nom}"
                value="${nettoyerTexte(valeur)}"
                checked
                onchange="mettreAJourParentSource('${cle}')">
            ${nettoyerTexte(valeur)}
        </label>
    `).join("");
}

async function chargerOptionsSources() {
    const div = document.getElementById("options_sources");

    try {
        const reponse = await fetch("/options_sources");
        const data = await reponse.json();

        const languesWiktionary = data.wiktionary?.langues || [];
        const editionsAcademie = data.academie_fr?.editions || [];

        div.innerHTML = `
            <details class="source-groupe-options">
                <summary class="source-summary">
                    <input type="checkbox"
                        name="sources"
                        value="wiktionary"
                        id="source_wiktionary"
                        checked
                        onclick="event.stopPropagation()"
                        onchange="basculerGroupeSource('wiktionary')">

                    <span class="source-nom">Wiktionary</span>
                </summary>

                <div class="liste-sous-sources">
                    ${creerCasesEnfants("wiktionary_langues", languesWiktionary, "wiktionary")}
                </div>
            </details>

            <label>
                <input type="checkbox" name="sources" value="larousse" checked>
                Larousse
            </label>

            <label>
                <input type="checkbox" name="sources" value="littre">
                Littré
            </label>

            <details class="source-groupe-options">
                <summary class="source-summary">
                    <input type="checkbox"
                        name="sources"
                        value="academie_fr"
                        id="source_academie_fr"
                        checked
                        onclick="event.stopPropagation()"
                        onchange="basculerGroupeSource('academie_fr')">

                    <span class="source-nom">Académie française</span>
                </summary>

                <div class="liste-sous-sources">
                    ${creerCasesEnfants("academie_fr_editions", editionsAcademie, "academie_fr")}
                </div>
            </details>
        `;

        mettreAJourParentSource("wiktionary");
        mettreAJourParentSource("academie_fr");

    } catch (erreur) {
        div.innerHTML = `
            <p style="color: #b00020;">Impossible de charger les options de sources.</p>
        `;
        console.error(erreur);
    }
}

function nettoyerTexte(texte) {
    return String(texte ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function afficherSourcesUtilisees(sources) {
    if (!Array.isArray(sources) || sources.length === 0) {
        return "";
    }

    if (sources.length <= 6) {
        return `
            <p class="sources-utilisees">
                <strong>Sources utilisées :</strong>
                ${sources.map(s => nettoyerTexte(s)).join(", ")}
            </p>
        `;
    }

    const resume = sources
        .slice(0, 4)
        .map(s => nettoyerTexte(s))
        .join(", ");

    const listeComplete = sources
        .map(s => `<li>${nettoyerTexte(s)}</li>`)
        .join("");

    return `
        <details class="sources-utilisees sources-pliables">
            <summary>
                <strong>Sources utilisées :</strong>
                ${resume}, et ${sources.length - 4} autres
            </summary>

            <ul>
                ${listeComplete}
            </ul>
        </details>
    `;
}

function afficherListeSimple(elements) {
    if (!Array.isArray(elements) || elements.length === 0) {
        return "";
    }

    return `
        <ul>
            ${elements.map(element => `
                <li>${nettoyerTexte(element)}</li>
            `).join("")}
        </ul>
    `;
}

async function chargerSourcesBrutes(mot) {
    const div = document.getElementById("sources_brutes");

    if (!div) {
        return;
    }

    div.innerHTML = `<p class="message">Chargement des sources...</p>`;

    try {
        const reponse = await fetch(`/sources?mot=${encodeURIComponent(mot)}`);
        const sources = await reponse.json();

        if (!reponse.ok) {
            throw new Error("Impossible de charger les sources.");
        }

        if (!Array.isArray(sources) || sources.length === 0) {
            div.innerHTML = `
                <p class="message">Aucune source brute disponible pour ce mot.</p>
            `;
            return;
        }

        const groupes = {};

        for (const source of sources) {
            const nom = source.source || "Source inconnue";

            if (!groupes[nom]) {
                groupes[nom] = [];
            }

            groupes[nom].push(source);
        }

        const nomsGroupes = Object.keys(groupes).sort((a, b) =>
            a.localeCompare(b, "fr", { sensitivity: "base" })
        );

        div.innerHTML = nomsGroupes.map(nomGroupe => {
            const elements = groupes[nomGroupe].sort((a, b) => {
                const aTexte = `${a.page_titre || ""} ${a.langue || ""}`;
                const bTexte = `${b.page_titre || ""} ${b.langue || ""}`;
                return aTexte.localeCompare(bTexte, "fr", { sensitivity: "base" });
            });

            const totalCaracteres = elements.reduce(
                (somme, source) => somme + Number(source.taille || 0),
                0
            );

            return `
                <details class="groupe-source">
                    <summary>
                        <strong>${nettoyerTexte(nomGroupe)}</strong>
                        <span class="meta">
                            — ${elements.length} entrée${elements.length > 1 ? "s" : ""}
                            — ${totalCaracteres.toLocaleString("fr-FR")} caractères
                        </span>
                    </summary>

                    <div class="liste-sources-groupe">
                        ${elements.map(source => {
                            const titre = source.page_titre
                                ? `${source.page_titre} — ${source.langue}`
                                : source.langue;

                            return `
                                <div class="source-brute">
                                    <strong>${nettoyerTexte(titre || "Entrée")}</strong>
                                    <br>

                                    <span class="petit">
                                        ${Number(source.taille || 0).toLocaleString("fr-FR")} caractères
                                    </span>

                                    <div class="actions-source">
                                        ${source.url ? `
                                            <a href="${nettoyerTexte(source.url)}"
                                            target="_blank"
                                            rel="noopener noreferrer">
                                                Ouvrir le site
                                            </a>
                                        ` : ""}

                                        <button class="mini-bouton secondaire"
                                                onclick="basculerSourceBrute(${Number(source.id)})">
                                            Voir le brut
                                        </button>
                                    </div>

                                    <div id="source_brute_${Number(source.id)}"></div>
                                </div>
                            `;
                        }).join("")}
                    </div>
                </details>
            `;
        }).join("");

    } catch (erreur) {
        div.innerHTML = `
            <p style="color: #b00020;">${nettoyerTexte(erreur.message)}</p>
        `;
    }
}

async function basculerSourceBrute(id) {
    const div = document.getElementById(`source_brute_${id}`);

    if (!div) {
        return;
    }

    if (div.dataset.ouvert === "1") {
        div.innerHTML = "";
        div.dataset.ouvert = "0";
        return;
    }

    div.innerHTML = `<p class="message">Chargement du brut...</p>`;

    try {
        const reponse = await fetch(`/source_brute?id=${encodeURIComponent(id)}`);
        const data = await reponse.json();

        if (!reponse.ok || data.erreur) {
            throw new Error(data.message || "Impossible de charger la source brute.");
        }

        div.innerHTML = `
            <details open class="bloc-brut-source">
                <summary>Source brute enregistrée</summary>
                <pre>${nettoyerTexte(data.contenu_brut || "")}</pre>
            </details>
        `;

        div.dataset.ouvert = "1";

    } catch (erreur) {
        div.innerHTML = `
            <p style="color: #b00020;">${nettoyerTexte(erreur.message)}</p>
        `;
    }
}

function cocherValeurs(nom, valeursCSV) {
    const valeurs = new Set(
        String(valeursCSV || "")
            .split(",")
            .map(v => v.trim())
            .filter(Boolean)
    );

    document.querySelectorAll(`input[name="${nom}"]`).forEach(input => {
        input.checked = valeurs.has(input.value);
    });
}

function demanderConfirmationSuppression() {
    if (!generationOuverte) {
        return;
    }

    const ancienneFenetre = document.getElementById("modal_confirmation_suppression");

    if (ancienneFenetre) {
        ancienneFenetre.remove();
    }

    document.body.insertAdjacentHTML("beforeend", `
        <div class="modal-fond" id="modal_confirmation_suppression" onclick="clicFondConfirmation(event)">
            <div class="modal-carte">
                <h3>Supprimer cette génération ?</h3>

                <p>
                    Cette action supprimera définitivement la fiche ouverte.
                </p>

                <p class="petit">
                    Mot concerné : <strong>${nettoyerTexte(generationOuverte.mot || "")}</strong>
                </p>

                <div class="modal-actions">
                    <button class="danger" onclick="confirmerSuppressionGeneration()">
                        Supprimer
                    </button>

                    <button class="secondaire" onclick="fermerConfirmationSuppression()">
                        Annuler
                    </button>
                </div>
            </div>
        </div>
    `);
}

function fermerConfirmationSuppression() {
    const fenetre = document.getElementById("modal_confirmation_suppression");

    if (fenetre) {
        fenetre.remove();
    }
}

function clicFondConfirmation(event) {
    if (event.target.id === "modal_confirmation_suppression") {
        fermerConfirmationSuppression();
    }
}

async function confirmerSuppressionGeneration() {
    fermerConfirmationSuppression();
    await supprimerGenerationOuverte();
}

async function supprimerGenerationOuverte() {
    if (!generationOuverte) {
        alert("Aucune génération ouverte.");
        return;
    }

    const mot = generationOuverte.mot;
    const id = generationOuverte.id;

    try {
        const reponse = await fetch(`/generation?id=${encodeURIComponent(id)}`, {
            method: "DELETE"
        });

        const data = await reponse.json();

        if (!reponse.ok || data.erreur) {
            throw new Error(data.message || "Suppression impossible.");
        }

        generationOuverte = null;

        document.getElementById("generation_ouverte").innerHTML = `
            <p class="message">Génération supprimée.</p>
        `;

        afficherMessage("Génération supprimée.");
        await chargerGenerations(mot);
        await chargerSourcesBrutes(mot);

    } catch (erreur) {
        afficherErreur(erreur.message);
    }
}

async function regenererGenerationOuverte() {
    if (!generationOuverte) {
        alert("Aucune génération ouverte.");
        return;
    }

    const ancienne = generationOuverte;

    document.getElementById("mot").value = ancienne.mot || "";
    document.getElementById("style").value = ancienne.style || "académique";
    document.getElementById("longueur").value = ancienne.longueur || "moyenne";
    document.getElementById("requete").value = ancienne.requete_utilisateur || "";

    cocherValeurs("sources", ancienne.sources_choisies);
    cocherValeurs("categories", ancienne.categories_choisies);

    afficherMessage(`Régénération de « ${ancienne.mot} »...`);

    await genererPersonnalise();
}

function motActuel() {
    return document.getElementById("mot").value.trim().toLowerCase();
}

function afficherMessage(message) {
    document.getElementById("resultat").innerHTML = `
        <p class="message">${nettoyerTexte(message)}</p>
    `;
}

function afficherErreur(message) {
    document.getElementById("resultat").innerHTML = `
        <p style="color: #b00020;"><strong>Erreur :</strong> ${nettoyerTexte(message)}</p>
    `;
}

async function consulterMot() {
    const mot = motActuel();

    if (!mot) {
        alert("Entre un mot !");
        return;
    }

    history.pushState(null, "", urlDictionnaire(mot));

    afficherMessage(`Chargement des générations enregistrées pour « ${mot} »...`);
    document.getElementById("generation_ouverte").innerHTML = `
        <p class="message">Choisis une génération dans la liste.</p>
    `;

    await chargerGenerations(mot);
    await chargerSourcesBrutes(mot);
    afficherMessage(`Générations affichées pour « ${mot} ». Aucun téléchargement Internet n’a été lancé.`);
}

async function rechercherSources() {
    const mot = motActuel();

    if (!mot) {
        alert("Entre un mot !");
        return;
    }

    afficherMessage(`Recherche / mise à jour des sources pour « ${mot} »...`);

    try {
        const reponse = await fetch(`/chercher?mot=${encodeURIComponent(mot)}`);
        const data = await reponse.json();

        if (!reponse.ok) {
            throw new Error(data.detail || "La recherche a échoué.");
        }

        document.getElementById("resultat").innerHTML = `
            <h3>${nettoyerTexte(data.mot || mot)}</h3>
            <p><strong>Résumé :</strong> ${nettoyerTexte(data.resume)}</p>
            <p><strong>Sources :</strong> ${nettoyerTexte(data.sources)}</p>
            <p><strong>Date :</strong> ${nettoyerTexte(data.date)}</p>
        `;

        await chargerGenerations(mot);
        await chargerSourcesBrutes(mot);
    } catch (erreur) {
        afficherErreur(erreur.message);
    }
}

async function chargerGenerations(mot) {
    const div = document.getElementById("generations");
    div.innerHTML = `<p class="message">Chargement...</p>`;

    try {
        const reponse = await fetch(`/generations?mot=${encodeURIComponent(mot)}`);
        const generations = await reponse.json();

        if (!reponse.ok) {
            throw new Error("Impossible de charger les générations.");
        }

        div.innerHTML = "";

        if (!Array.isArray(generations) || generations.length === 0) {
            div.innerHTML = `
                <p class="message">Aucune génération enregistrée pour ce mot.</p>
            `;
            return;
        }

        generations.forEach(gen => {
            const bouton = document.createElement("button");
            bouton.className = "generation-bouton";
            bouton.innerHTML = `
                ${nettoyerTexte(gen.date)}<br>
                <span class="meta">${nettoyerTexte(gen.style)} • ${nettoyerTexte(gen.longueur)}</span>
            `;
            bouton.onclick = () => ouvrirGeneration(gen.id);
            div.appendChild(bouton);
        });
    } catch (erreur) {
        div.innerHTML = `
            <p style="color: #b00020;">${nettoyerTexte(erreur.message)}</p>
        `;
    }
}

function utilisateurPeutSupprimerGeneration(generation) {
    if (!utilisateurActuel) {
        return false;
    }

    if (utilisateurActuel.role === "admin") {
        return true;
    }

    // Pour les anciennes générations anonymes.
    // À garder seulement si ton backend autorise leur suppression par un utilisateur connecté.
    if (generation.user_id === null || generation.user_id === undefined || generation.user_id === "") {
        return true;
    }

    return Number(generation.user_id) === Number(utilisateurActuel.id);
}

async function ouvrirGeneration(id) {
    try {
        const reponse = await fetch(`/generation?id=${encodeURIComponent(id)}`);
        const data = await reponse.json();

        generationOuverte = data;
        history.pushState(null, "", urlDictionnaire(data.mot, data.id));
        let contenuHTML = "";

        try {
            const json = JSON.parse(data.contenu);

            contenuHTML += `
                <div class="generation-jolie">
                    <h2>${nettoyerTexte(json.mot || data.mot)}</h2>

                    <div class="meta">
                        ${nettoyerTexte(data.date_generation || "")}
                        —
                        ${nettoyerTexte(data.style || "")}
                        —
                        ${nettoyerTexte(data.longueur || "")}
                    </div>

                    <h3>Résumé général</h3>
                    <p>${nettoyerTexte(json.resume_general || "")}</p>
            `;

            if (json.fiabilite) {
                contenuHTML += `
                    <h3>Fiabilité</h3>
                    <p>
                        <strong>Niveau :</strong>
                        ${nettoyerTexte(json.fiabilite.niveau || "inconnu")}
                    </p>
                    <p>${nettoyerTexte(json.fiabilite.justification || "")}</p>
                `;
            }

            if (json.sens && Array.isArray(json.sens) && json.sens.length > 0) {
                contenuHTML += `<h3>Sens distingués</h3>`;

                for (const sens of json.sens) {
                    contenuHTML += `
                        <div class="section-generation">
                            <h4>${nettoyerTexte(sens.titre || "Sens")}</h4>
                            <p class="meta">${nettoyerTexte(sens.type || "type non précisé")}</p>
                            <p>${nettoyerTexte(sens.description || "").replaceAll("\n", "<br>")}</p>
                    `;

                    if (sens.exemples && Array.isArray(sens.exemples) && sens.exemples.length > 0) {
                        contenuHTML += `
                            <p><strong>Exemples :</strong></p>
                            ${afficherListeSimple(sens.exemples)}
                        `;
                    }

                    contenuHTML += afficherSourcesUtilisees(sens.sources_utilisees);
                    contenuHTML += `</div>`;
                }
            }

            if (json.sections && Array.isArray(json.sections)) {
                for (const section of json.sections) {
                    contenuHTML += `
                        <div class="section-generation">
                            <h3>${nettoyerTexte(section.titre || "Section")}</h3>
                            <p>${nettoyerTexte(section.contenu || "").replaceAll("\n", "<br>")}</p>
                    `;

                    contenuHTML += afficherSourcesUtilisees(section.sources_utilisees);
                    contenuHTML += `</div>`;
                }
            }

            if (json.contradictions_ou_incertain && json.contradictions_ou_incertain.length > 0) {
                contenuHTML += `
                    <h3>Contradictions ou points incertains</h3>
                    ${afficherListeSimple(json.contradictions_ou_incertain)}
                `;
            }

            if (json.informations_absentes && json.informations_absentes.length > 0) {
                contenuHTML += `
                    <h3>Informations absentes</h3>
                    ${afficherListeSimple(json.informations_absentes)}
                `;
            }

            contenuHTML += `</div>`;

        } catch (erreurJSON) {
            contenuHTML = `
                <h2>${nettoyerTexte(data.mot)}</h2>
                <div class="meta">
                    ${nettoyerTexte(data.date_generation || "")}
                    —
                    ${nettoyerTexte(data.style || "")}
                    —
                    ${nettoyerTexte(data.longueur || "")}
                </div>
                <pre>${nettoyerTexte(data.contenu || "")}</pre>
            `;
        }

        document.getElementById("generation_ouverte").innerHTML = `
            <div class="actions-generation">
                <button class="secondaire" onclick="regenererGenerationOuverte()">🔁 Régénérer</button>

                ${utilisateurPeutSupprimerGeneration(data) ? `
                    <button class="danger" onclick="demanderConfirmationSuppression()">
                        🗑️ Supprimer
                    </button>
                ` : ""}
            </div>

            ${data.nom_utilisateur ? `
                <p>
                    <strong>Créée par :</strong>
                    ${data.identifiant_public ? `
                        <a href="/utilisateur/${encodeURIComponent(data.identifiant_public)}"
                        onclick="event.preventDefault(); ouvrirProfilUtilisateur('${encodeURIComponent(data.identifiant_public)}')">
                            ${nettoyerTexte(data.nom_utilisateur)}
                        </a>
                    ` : `
                        ${nettoyerTexte(data.nom_utilisateur)}
                    `}
                </p>
            ` : `
                <p>
                    <strong>Créée par :</strong>
                    Anonyme
                </p>
            `}

            <p>
                <strong>Requête :</strong>
                ${nettoyerTexte(data.requete_utilisateur || "Aucune")}
            </p>

            <p>
                <strong>Sources :</strong>
                ${nettoyerTexte(data.sources_choisies || "Toutes")}
            </p>

            <p>
                <strong>Catégories :</strong>
                ${nettoyerTexte(data.categories_choisies || "Toutes")}
            </p>

            <hr>

            ${contenuHTML}
        `;

        afficherMessage(`Génération ouverte : « ${data.mot} ».`);

    } catch (erreur) {
        afficherErreur("Impossible d’ouvrir la génération.");
        console.error(erreur);
    }
}

async function genererPersonnalise() {
    const mot = motActuel();

    if (!mot) {
        alert("Entre un mot !");
        return;
    }

    if (!utilisateurActuel) {
        afficherErreur("Tu dois être connecté pour créer une fiche.");
        return;
    }

    const style = document.getElementById("style").value;
    const longueur = document.getElementById("longueur").value;
    const requete = document.getElementById("requete").value.trim();
    const reutiliserSources = document.getElementById("reutiliser_sources").checked;
    const modeTestPrompt = document.getElementById("mode_test_prompt").checked;
    
    const sources = recupererSourcesSelectionnees();

    if (sources.length === 0) {
        afficherErreur("Choisis au moins une source pour générer une fiche.");
        return;
    }

    const categories = Array.from(document.querySelectorAll('input[name="categories"]:checked'))
        .map(input => input.value);

    afficherMessage(`Génération personnalisée pour « ${mot} »...`);

    const filtresSources = {
        wiktionary: {
            langues: Array.from(document.querySelectorAll('input[name="wiktionary_langues"]:checked'))
                .map(input => input.value)
        },
        academie_fr: {
            editions: Array.from(document.querySelectorAll('input[name="academie_fr_editions"]:checked'))
                .map(input => input.value)
        }
    };

    try {
        const reponse = await fetch("/generer_personnalise", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                mot: mot,
                style: style,
                longueur: longueur,
                requete: requete,
                sources: sources,
                categories: categories,
                reutiliser_sources: reutiliserSources,
                mode_test: modeTestPrompt,
                filtres_sources: filtresSources
            })
        });
        const data = await reponse.json();
        if (data.erreur) {
            document.getElementById("generation_ouverte").innerHTML = `
                <p style="color: #b00020;">
                    <strong>Erreur IA :</strong>
                    ${nettoyerTexte(data.message || "Erreur inconnue.")}
                </p>

                ${data.prompt ? `
                    <details>
                        <summary>Voir le prompt envoyé</summary>
                        <pre>${nettoyerTexte(data.prompt)}</pre>
                    </details>
                ` : ""}
            `;

            afficherErreur(data.message || "Erreur lors de l’appel à l’IA.");
            return;
        }

        if (data.mode_test) {
            document.getElementById("generation_ouverte").innerHTML = `
                <h3>Mode test : prompt généré</h3>
                <p class="message">L’IA n’a pas été appelée.</p>

                <details open>
                    <summary>Voir le prompt</summary>
                    <pre>${nettoyerTexte(data.prompt || data.contenu || "")}</pre>
                </details>
            `;

            afficherMessage(data.message || "Prompt généré.");
            await chargerSourcesBrutes(mot);
            return;
        }

        if (!reponse.ok) {
            throw new Error(data.detail || "La génération a échoué.");
        }

        afficherMessage(data.message || "Génération enregistrée.");
        await chargerGenerations(mot);

        if (data.id) {
            await ouvrirGeneration(data.id);
        }
    } catch (erreur) {
        afficherErreur(erreur.message);
    }
}

function groupeSourceActif(cle) {
    const groupe = groupesSources[cle];
    const parent = document.getElementById(groupe.parentId);
    const enfants = Array.from(
        document.querySelectorAll(`input[name="${groupe.enfantsName}"]`)
    );

    return Boolean(
        parent?.checked ||
        parent?.indeterminate ||
        enfants.some(enfant => enfant.checked)
    );
}

function recupererSourcesSelectionnees() {
    const sources = [];

    if (groupeSourceActif("wiktionary")) {
        sources.push("wiktionary");
    }

    const larousse = document.querySelector('input[name="sources"][value="larousse"]');
    if (larousse?.checked) {
        sources.push("larousse");
    }

    const littre = document.querySelector('input[name="sources"][value="littre"]');
    if (littre?.checked) {
        sources.push("littre");
    }

    if (groupeSourceActif("academie_fr")) {
        sources.push("academie_fr");
    }

    return sources;
}

function afficherMessageCompteModal(message, type = "") {
    const element = document.getElementById("message_compte_modal");

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = "message-compte";

    if (type) {
        element.classList.add(type);
    }
}

async function ouvrirCompte() {
    memoriserURLDictionnaire();

    if (!utilisateurActuel) {
        afficherErreur("Tu dois être connecté pour accéder à ton compte.");
        return;
    }

    const hero = document.querySelector(".hero");
    const grille = document.querySelector(".grille");
    const pageCompte = document.getElementById("page_compte");

    if (hero) hero.classList.add("cache");
    if (grille) grille.classList.add("cache");
    if (pageCompte) pageCompte.classList.remove("cache");

    history.pushState(null, "", "/compte");

    document.getElementById("compte_pseudo_actuel").textContent =
        utilisateurActuel.nom_utilisateur || "—";

    document.getElementById("compte_email_actuel").textContent =
        utilisateurActuel.email || "—";

    document.getElementById("compte_identifiant_public").textContent =
        utilisateurActuel.identifiant_public || "—";

    document.getElementById("nouveau_pseudo").value =
        utilisateurActuel.nom_utilisateur || "";

    document.getElementById("nouvel_email").value =
        utilisateurActuel.email || "";

    afficherMessageCompteModal("");
    await chargerMesFiches();
}

function fermerCompte() {
    const hero = document.querySelector(".hero");
    const grille = document.querySelector(".grille");
    const pageCompte = document.getElementById("page_compte");
    const pageUtilisateur = document.getElementById("page_utilisateur");

    if (hero) hero.classList.remove("cache");
    if (grille) grille.classList.remove("cache");
    if (pageCompte) pageCompte.classList.add("cache");
    if (pageUtilisateur) pageUtilisateur.classList.add("cache");

    history.pushState(null, "", derniereURLDictionnaire || "/");
}

async function ouvrirProfilUtilisateur(idProfilEncode) {
    memoriserURLDictionnaire();

    const idProfil = decodeURIComponent(idProfilEncode);

    const hero = document.querySelector(".hero");
    const grille = document.querySelector(".grille");
    const pageCompte = document.getElementById("page_compte");
    const pageUtilisateur = document.getElementById("page_utilisateur");

    if (hero) hero.classList.add("cache");
    if (grille) grille.classList.add("cache");
    if (pageCompte) pageCompte.classList.add("cache");
    if (pageUtilisateur) pageUtilisateur.classList.remove("cache");

    history.pushState(
        null,
        "",
        `/utilisateur/${encodeURIComponent(idProfil)}`
    );

    document.getElementById("profil_nom_utilisateur").textContent = "—";
    document.getElementById("profil_id_profil").textContent = idProfil;
    document.getElementById("profil_fiches").innerHTML = `
        <p class="message">Chargement...</p>
    `;

    try {
        const reponse = await fetch(`/api/utilisateur/${encodeURIComponent(idProfil)}`);
        const data = await reponse.json();

        if (data.erreur) {
            throw new Error(data.message || "Utilisateur introuvable.");
        }

        document.getElementById("profil_nom_utilisateur").textContent =
            data.utilisateur.nom_utilisateur || "—";

        document.getElementById("profil_id_profil").textContent =
            data.utilisateur.id_profil || "—";

        document.getElementById("profil_date_creation").textContent =
            data.utilisateur.date_creation || "—";

        document.getElementById("profil_role").textContent =
            data.utilisateur.role || "—";

        const div = document.getElementById("profil_fiches");

        if (!data.generations || data.generations.length === 0) {
            div.innerHTML = `<p class="message">Cet utilisateur n’a encore créé aucune fiche.</p>`;
            return;
        }

        div.innerHTML = data.generations.map(gen => `
            <div class="fiche-compte">
                <div class="fiche-compte-ligne">
                    <div>
                        <strong>${nettoyerTexte(gen.mot)}</strong>
                        <div class="meta">
                            ${nettoyerTexte(gen.date_generation || "")}
                            —
                            ${nettoyerTexte(gen.style || "")}
                            —
                            ${nettoyerTexte(gen.longueur || "")}
                        </div>
                    </div>

                    <button type="button"
                            class="secondaire mini-bouton"
                            onclick="ouvrirFicheDepuisCompte('${encodeURIComponent(gen.mot)}', ${Number(gen.id)})">
                        Ouvrir
                    </button>
                </div>
            </div>
        `).join("");

    } catch (erreur) {
        document.getElementById("profil_fiches").innerHTML = `
            <p style="color: #b00020;">${nettoyerTexte(erreur.message)}</p>
        `;
    }
}

async function chargerMesFiches() {
    const div = document.getElementById("mes_fiches");

    if (!div) {
        return;
    }

    div.innerHTML = `<p class="message">Chargement...</p>`;

    try {
        const reponse = await fetch("/mes_generations");
        const data = await reponse.json();

        if (data.erreur) {
            throw new Error(data.message || "Impossible de charger les fiches.");
        }

        if (!data.generations || data.generations.length === 0) {
            div.innerHTML = `<p class="message">Aucune fiche créée avec ce compte.</p>`;
            return;
        }

        div.innerHTML = data.generations.map(gen => `
            <div class="fiche-compte">
                <strong>${nettoyerTexte(gen.mot)}</strong>
                <div class="meta">
                    ${nettoyerTexte(gen.date_generation || "")}
                    —
                    ${nettoyerTexte(gen.style || "")}
                    —
                    ${nettoyerTexte(gen.longueur || "")}
                </div>

                <button type="button"
                        class="secondaire mini-bouton"
                        onclick="ouvrirFicheDepuisCompte('${encodeURIComponent(gen.mot)}', ${Number(gen.id)})">
                    Ouvrir
                </button>
            </div>
        `).join("");

    } catch (erreur) {
        div.innerHTML = `<p style="color: #b00020;">${nettoyerTexte(erreur.message)}</p>`;
    }
}

async function ouvrirFicheDepuisCompte(motEncode, id) {
    const mot = decodeURIComponent(motEncode);

    const hero = document.querySelector(".hero");
    const grille = document.querySelector(".grille");
    const pageCompte = document.getElementById("page_compte");
    const pageUtilisateur = document.getElementById("page_utilisateur");

    if (hero) hero.classList.remove("cache");
    if (grille) grille.classList.remove("cache");
    if (pageCompte) pageCompte.classList.add("cache");
    if (pageUtilisateur) pageUtilisateur.classList.add("cache");

    document.getElementById("mot").value = mot;

    await chargerGenerations(mot);
    await chargerSourcesBrutes(mot);
    await ouvrirGeneration(id);
}

async function modifierPseudoCompte(event) {
    event.preventDefault();

    const nouveauNom = document.getElementById("nouveau_pseudo").value.trim();
    const motDePasse = document.getElementById("mdp_pseudo").value;

    try {
        const reponse = await fetch("/compte/pseudo", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                nouveau_nom_utilisateur: nouveauNom,
                mot_de_passe: motDePasse
            })
        });

        const data = await reponse.json();

        if (data.erreur) {
            throw new Error(data.message || "Modification impossible.");
        }

        utilisateurActuel = data.utilisateur;
        afficherEtatCompte();
        document.getElementById("compte_pseudo_actuel").textContent =
        utilisateurActuel.nom_utilisateur || "—";
        afficherMessageCompteModal(data.message || "Pseudo modifié.", "ok");

        document.getElementById("mdp_pseudo").value = "";

        if (generationOuverte?.id) {
            await ouvrirGeneration(generationOuverte.id);
        }

    } catch (erreur) {
        afficherMessageCompteModal(erreur.message, "erreur");
    }
}

async function modifierEmailCompte(event) {
    event.preventDefault();

    const nouvelEmail = document.getElementById("nouvel_email").value.trim();
    const motDePasse = document.getElementById("mdp_email").value;

    try {
        const reponse = await fetch("/compte/email", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                nouvel_email: nouvelEmail,
                mot_de_passe: motDePasse
            })
        });

        const data = await reponse.json();

        if (data.erreur) {
            throw new Error(data.message || "Modification impossible.");
        }

        utilisateurActuel = data.utilisateur;
        afficherEtatCompte();
        document.getElementById("compte_email_actuel").textContent =
        utilisateurActuel.email || "—";
        afficherMessageCompteModal(data.message || "E-mail modifié.", "ok");

        document.getElementById("mdp_email").value = "";

    } catch (erreur) {
        afficherMessageCompteModal(erreur.message, "erreur");
    }
}

async function modifierMotDePasseCompte(event) {
    event.preventDefault();

    const ancien = document.getElementById("ancien_mdp").value;
    const nouveau = document.getElementById("nouveau_mdp").value;

    try {
        const reponse = await fetch("/compte/mot_de_passe", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                ancien_mot_de_passe: ancien,
                nouveau_mot_de_passe: nouveau
            })
        });

        const data = await reponse.json();

        if (data.erreur) {
            throw new Error(data.message || "Modification impossible.");
        }

        afficherMessageCompteModal(data.message || "Mot de passe modifié.", "ok");

        document.getElementById("ancien_mdp").value = "";
        document.getElementById("nouveau_mdp").value = "";

    } catch (erreur) {
        afficherMessageCompteModal(erreur.message, "erreur");
    }
}

async function initialiserInterface() {
    console.log("Script chargé : initialisation de l’interface.");

    const champMot = document.getElementById("mot");

    if (champMot) {
        champMot.addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                consulterMot();
            }
        });
    }

    const retourProfil = document.getElementById("retour_profil");

    if (retourProfil) {
        retourProfil.addEventListener("click", fermerCompte);
    }

    const ongletConnexion = document.getElementById("onglet_connexion");
    const ongletInscription = document.getElementById("onglet_inscription");
    const formConnexion = document.getElementById("form_connexion");
    const formInscription = document.getElementById("form_inscription");
    const boutonDeconnexion = document.getElementById("bouton_deconnexion");

    const boutonCompte = document.getElementById("bouton_compte");
    const retourCompte = document.getElementById("retour_compte");

    const formModifierPseudo = document.getElementById("form_modifier_pseudo");
    const formModifierEmail = document.getElementById("form_modifier_email");
    const formModifierMdp = document.getElementById("form_modifier_mdp");

    if (ongletConnexion) {
        ongletConnexion.addEventListener("click", () => {
            changerModeCompte("connexion");
        });
    }

    if (ongletInscription) {
        ongletInscription.addEventListener("click", () => {
            changerModeCompte("inscription");
        });
    }

    if (formConnexion) {
        formConnexion.addEventListener("submit", event => {
            event.preventDefault();
            connexionCompte();
        });
    }

    if (formInscription) {
        formInscription.addEventListener("submit", event => {
            event.preventDefault();
            inscriptionCompte();
        });
    }

    if (boutonDeconnexion) {
        boutonDeconnexion.addEventListener("click", () => {
            deconnexionCompte();
        });
    }

    if (boutonCompte) {
        boutonCompte.addEventListener("click", ouvrirCompte);
    }

    if (retourCompte) {
        retourCompte.addEventListener("click", fermerCompte);
    }

    if (formModifierPseudo) {
        formModifierPseudo.addEventListener("submit", modifierPseudoCompte);
    }

    if (formModifierEmail) {
        formModifierEmail.addEventListener("submit", modifierEmailCompte);
    }

    if (formModifierMdp) {
        formModifierMdp.addEventListener("submit", modifierMotDePasseCompte);
    }

    await chargerOptionsSources();
    await chargerCompte();
    await chargerDepuisURL();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialiserInterface);
} else {
    initialiserInterface();
}