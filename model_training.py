import os
from imutils import paths
import face_recognition
import pickle
import cv2
print("[INFO] start processing faces...")
imagePaths = list(paths.list_images("dataset"))
knownEncodings = []
knownNames = []
faces_found = 0
for (i, imagePath) in enumerate(imagePaths):
   print(f"[INFO] processing image {i + 1}/{len(imagePaths)}")
   name = imagePath.split(os.path.sep)[-2]
   image = cv2.imread(imagePath)
   if image is None:
       print(f"[WARN] Could not read {imagePath}")
       continue
   image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
   rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
   boxes = face_recognition.face_locations(rgb, model="hog")
   print(f"[DEBUG] {name}: {len(boxes)} face(s) found")
   if len(boxes) == 0:
       continue
   encodings = face_recognition.face_encodings(rgb, boxes)
   for encoding in encodings:
       knownEncodings.append(encoding)
       knownNames.append(name)
       faces_found += 1
print(f"[DEBUG] Total encodings collected: {faces_found}")
print("[INFO] serializing encodings...")
data = {"encodings": knownEncodings, "names": knownNames}
with open("encodings.pickle", "wb") as f:
   f.write(pickle.dumps(data))
print("[INFO] Training complete. Encodings saved to 'encodings.pickle'")
