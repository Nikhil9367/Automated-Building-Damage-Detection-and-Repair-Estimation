import os
import json
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODEL_DIR = os.path.join(BASE_DIR, "model")
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 0.0001

def train():
    print("Checking dataset...")
    if not os.path.exists(DATASET_DIR):
        print(f"Error: Dataset directory '{DATASET_DIR}' not found.")
        print("Please create it and add your images in subfolders (e.g., dataset/crack, dataset/spall).")
        return

    # Count classes
    classes = [d for d in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, d))]
    if not classes:
        print("No class folders found in dataset directory.")
        return
    
    print(f"Found {len(classes)} classes: {classes}")
    
    # Check if there are images
    # Data Augmentation & Loading
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        horizontal_flip=True,
        validation_split=0.2
    )

    train_generator = train_datagen.flow_from_directory(
        DATASET_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='training'
    )

    validation_generator = train_datagen.flow_from_directory(
        DATASET_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        subset='validation'
    )
    
    # Calculate class weights
    from sklearn.utils import class_weight
    import numpy as np

    # Get class indices from generator
    class_indices = train_generator.class_indices
    # Map class indices to class names
    idx_to_class = {v: k for k, v in class_indices.items()}
    
    # Get labels for all samples
    y_train = train_generator.classes
    
    # Calculate weights
    class_weights_vals = class_weight.compute_class_weight(
        class_weight='balanced',
        classes=np.unique(y_train),
        y=y_train
    )
    

    class_weights = dict(enumerate(class_weights_vals))
    print(f"Class weights: {class_weights}")
    
    # Base Model (ResNet50)
    base_model = ResNet50(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
    
    # Freeze base model layers initially
    for layer in base_model.layers:
        layer.trainable = False

    # Custom Head
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dropout(0.5)(x)
    x = Dense(1024, activation='relu')(x)
    predictions = Dense(len(classes), activation='softmax')(x)

    model = Model(inputs=base_model.input, outputs=predictions)

    model.compile(optimizer=Adam(learning_rate=LEARNING_RATE), 
                  loss='categorical_crossentropy', 
                  metrics=['accuracy'])

    # Train
    # Train
    print("Training model...")
    history = model.fit(
        train_generator,
        steps_per_epoch=train_generator.samples // BATCH_SIZE,
        validation_data=validation_generator,
        validation_steps=validation_generator.samples // BATCH_SIZE,
        epochs=EPOCHS
        # class_weight=class_weights
    )

    # Save Model
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "damage_model.h5")
    model.save(model_path)
    print(f"Model saved to {model_path}")

    # Save Class Indices
    indices_path = os.path.join(MODEL_DIR, "class_indices.json")
    with open(indices_path, "w") as f:
        # train_generator.class_indices is {'class_name': 0, ...}
        # We want to save it to map back later
        json.dump(train_generator.class_indices, f)
    print(f"Class indices saved to {indices_path}")

if __name__ == "__main__":
    train()
