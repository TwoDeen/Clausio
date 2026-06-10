import sys
import spacy


def decompose_into_clauses_fallback(text):
    try:
        # Using the standard GiNZA pipeline
        nlp = spacy.load("ja_ginza")
    except OSError:
        print(
            "Error: GiNZA model not found. Please install it using: pip install ja-ginza",
            file=sys.stderr,
        )
        return

    doc = nlp(text)

    print(f"Original Text: {text}\n")
    print("--- Detected Clauses ---")

    for sent in doc.sents:
        for token in sent:
            # 1. Find tokens that act as the structural head of a clause.
            # 'ROOT' is the main clause. 'advcl' and 'acl' are subordinate/adjective clauses.
            if token.dep_ in ("ROOT", "advcl", "acl"):

                # 2. Double-check that this head is actually a predicate (Verb, Adjective, or Aux/Copula)
                if token.pos_ in ("VERB", "ADJ", "AUX", "NOUN", "PRON"):

                    # 3. Grab all words that depend on this head (its subtree)
                    clause_tokens = sorted(
                        list(token.subtree), key=lambda x: x.i
                    )

                    # 4. Turn those tokens back into a readable string
                    clause_text = "".join([t.text for t in clause_tokens])

                    # Print the result immediately to the terminal
                    print(f"- [{token.dep_} / Head: {token.lemma_}]: {clause_text}")


if __name__ == "__main__":
    sample_text = "雨が降っていたので、傘を買って家に帰りました。"

    if len(sys.argv) > 1:
        sample_text = sys.argv[1]

    decompose_into_clauses_fallback(sample_text)
