from sentence_transformers import SentenceTransformer

# Download from HuggingFace
model = SentenceTransformer("intfloat/e5-base-v2")

# Save to your local disk
model.save("./models/e5-base-v2/")
print("Model saved locally!")