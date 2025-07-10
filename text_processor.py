# Text processing logic using spaCy (if available)
import spacy

# --- Try to load spaCy model ---
NLP = None
MODEL_NAME = "en_core_web_sm"
try:
    NLP = spacy.load(MODEL_NAME)
    print(f"[Text Processor] Successfully loaded spaCy model '{MODEL_NAME}'.")
except OSError:
    print(f"[Text Processor] WARNING: Could not load spaCy model '{MODEL_NAME}'.")
    print("Please ensure spaCy is installed and the model is downloaded:")
    print(f"  pip install spacy")
    print(f"  python -m spacy download {MODEL_NAME}")
    NLP = None # Ensure NLP is None if loading failed
except ImportError:
    print("[Text Processor] WARNING: spaCy library not found.")
    print("Please ensure spaCy is installed:")
    print(f"  pip install spacy")
    NLP = None


def extract_entities_relations(text_content):
    """
    Extracts entities (Methods, Institutions, potentially Topics) from text
    using spaCy for Named Entity Recognition (NER).

    Args:
        text_content (str): The text from the research paper (e.g., abstract or full text).

    Returns:
        dict: A dictionary containing extracted entities.
              {
                  "entities": {
                      "methods": [{"name": "Method Name", "description": "Extracted from text"}, ...],
                      "institutions": [{"name": "Institution Name", "location": None}, ...],
                      "topics": [{"name": "Topic Name"}, ...] // Can be augmented by NLP
                  }
              }
    """
    print(f"\n[Text Processor] Analyzing text content (length: {len(text_content)} chars)...")

    extracted_data = {
        "entities": {
            "methods": [],
            "topics": [],
            "institutions": []
        }
    }

    if not text_content:
        print("[Text Processor] No text content provided for analysis.")
        return extracted_data

    if NLP is None:
        print("[Text Processor] spaCy NLP model not available. Skipping advanced text processing.")
        # Fallback to very basic keyword spotting (similar to previous placeholder)
        text_lower = text_content.lower()
        if "machine learning" in text_lower:
            extracted_data["entities"]["methods"].append({"name": "Machine Learning", "description": "Mentioned in text (basic detection)"})
        if "statistical analysis" in text_lower:
            extracted_data["entities"]["methods"].append({"name": "Statistical Analysis", "description": "Mentioned in text (basic detection)"})
        return extracted_data

    # Process the text with spaCy
    doc = NLP(text_content)

    # 1. Extract Institutions (ORG entities)
    seen_institutions = set()
    for ent in doc.ents:
        if ent.label_ == "ORG": # ORG typically refers to companies, agencies, institutions
            inst_name = ent.text.strip()
            if inst_name and inst_name not in seen_institutions:
                # Basic filtering for common phrases that are not institutions
                if "university press" not in inst_name.lower() and len(inst_name.split()) > 1:
                    extracted_data["entities"]["institutions"].append({"name": inst_name, "location": None}) # Location TBD
                    seen_institutions.add(inst_name)
                    print(f"[Text Processor] spaCy: Found potential institution (ORG): '{inst_name}'.")

    # 2. Extract Potential Methods (Noun Phrases, or specific keywords near verbs)
    # This is a heuristic and can be improved significantly.
    # For simplicity, let's look for some known method-related keywords within noun phrases.
    # A more advanced approach would involve training a custom NER model for methods
    # or using dependency parsing to find actions and objects.

    method_keywords = ["method", "technique", "approach", "algorithm", "model", "analysis", "study", "framework", "system", "platform"]
    seen_methods = set()

    for chunk in doc.noun_chunks:
        chunk_text_lower = chunk.text.lower()
        # Check if the noun chunk itself might be a method or contains method keywords
        # This is very broad.
        # Example: "a novel machine learning technique", "our proposed deep learning model"

        # Heuristic: If a noun chunk contains a method keyword, consider the whole chunk (or parts of it)
        has_method_keyword = False
        for mk in method_keywords:
            if mk in chunk_text_lower:
                has_method_keyword = True
                break

        if has_method_keyword or "learning" in chunk_text_lower or "neural network" in chunk_text_lower:
            method_name = chunk.text.strip()
            # Simplistic cleaning:
            method_name = method_name.replace("the ", "").replace("a ", "").replace("an ", "")
            method_name = ' '.join(method_name.split()) # Normalize whitespace

            if len(method_name.split()) > 1 and len(method_name.split()) < 7 and method_name not in seen_methods: # Avoid very short/long phrases
                 # Avoid adding keywords themselves as methods if they are part of a larger phrase.
                is_just_keyword = False
                for mk in method_keywords:
                    if method_name.lower() == mk:
                        is_just_keyword = True
                        break
                if not is_just_keyword:
                    extracted_data["entities"]["methods"].append({"name": method_name.capitalize(), "description": f"Extracted from text: {method_name}"})
                    seen_methods.add(method_name)
                    print(f"[Text Processor] spaCy: Found potential method (from noun chunk): '{method_name.capitalize()}'.")

    # 3. Augment Topics (e.g., from noun phrases that are not ORG/Method)
    # This is also very heuristic. True topic modeling is complex.
    # For now, this section will be left minimal as keyword input is primary for topics.
    # We could, for example, extract common noun phrases not captured as methods/orgs.

    print("[Text Processor] spaCy analysis complete (basic entity extraction).")
    return extracted_data

if __name__ == '__main__':
    sample_abstract_spacy = """
    This paper from the University of ExampleTech presents a novel deep learning model
    for knowledge graph construction. We also employed statistical analysis of variance.
    Our research, conducted at the Advanced Computing Institute, focuses on AI Ethics and
    the practical applications of our new system in the industry. The Stanford University Press
    published related foundational work. We used a recurrent neural network.
    """

    print("--- Running text_processor.py spaCy example ---")
    # This will only work if spaCy and the model are correctly installed and loaded.
    if NLP:
        extracted_info_spacy = extract_entities_relations(sample_abstract_spacy)

        print("\n--- Extracted Information (spaCy-based) ---")
        if extracted_info_spacy["entities"]["methods"]:
            print("Methods:")
            for m in extracted_info_spacy["entities"]["methods"]:
                print(f"  - {m['name']} (Description: {m.get('description', 'N/A')})")

        if extracted_info_spacy["entities"]["institutions"]:
            print("Institutions:")
            for i in extracted_info_spacy["entities"]["institutions"]:
                print(f"  - {i['name']} (Location: {i.get('location', 'N/A')})")

        if not extracted_info_spacy["entities"]["methods"] and \
           not extracted_info_spacy["entities"]["institutions"]:
            print("No specific methods or institutions extracted by spaCy placeholder logic.")
    else:
        print("\nSkipping spaCy example execution as model was not loaded.")

    print("\n--- Note ---")
    print("The above entity extraction is a basic demonstration using spaCy's default NER.")
    print("For research papers, custom training or more advanced NLP techniques (e.g., SciSpaCy, specific relation extraction models) would be beneficial.")

```
