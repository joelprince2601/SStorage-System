import cv2
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Load YOLOv4 model
net = cv2.dnn.readNet("yolov4.weights", "yolov4.cfg")
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# Load class names from coco.names file
with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]

# Define target classes mapping
target_classes = {
    'cup': 'Milk',
    'apple': 'apple',
    'tomato': 'Tomato',
    'banana': 'Banana',
    'orange': 'orange',
    'broccoli': 'broccoli'
}

# Define initial expiry information (in days)
expiry_info = {
    'Milk': 2,
    'apple': 5,
    'Tomato': 6,
    'Banana': 3,
    'orange': 6,
    'broccoli': 4
}

# Initialize count dictionary
product_counts = {name: 0 for name in target_classes.values()}

# Initialize expiry tracking and exp_value
expiry_tracking = {name: expiry for name, expiry in expiry_info.items()}
exp_value = {name: 0 for name in target_classes.values()}  # 0 = not detected, 1 = detected

last_update = datetime.now()

def update_expiry_dates():
    global last_update
    now = datetime.now()
    if (now - last_update).total_seconds() >= 30:
        for product in expiry_tracking:
            # Update expiry date only if exp_value is 1 and the product is detected
            if exp_value[product] == 1 and expiry_tracking[product] > 0:
                expiry_tracking[product] -= 1
        last_update = now

def draw_boxes(frame, detections, conf_threshold=0.5, nms_threshold=0.4):
    height, width = frame.shape[:2]
    boxes, confidences, class_ids = [], [], []
    detected_products = set()

    for out in detections:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]

            if confidence > conf_threshold:
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Apply Non-Max Suppression to remove duplicates
    indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

    if len(indices) > 0:
        for i in indices.flatten():  # Flattening indices to iterate correctly
            box = boxes[i]
            x, y, w, h = box
            label = str(classes[class_ids[i]])
            
            if label in target_classes:
                label_name = target_classes[label]
                product_counts[label_name] += 1  # Increment count
                detected_products.add(label_name)  # Track detected products

                # Set exp_value to 1 if this is the first detection
                if exp_value[label_name] == 0:
                    exp_value[label_name] = 1

                # Check if the product is expired
                is_expired = expiry_tracking[label_name] <= 0
                color = (0, 0, 255) if is_expired else (0, 255, 0)
                
                # Draw bounding box
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # Prepare text with count and expiry info
                text = f"{label_name}: {confidences[i]:.2f}"
                expiry = f"Expiry: {expiry_tracking[label_name]} days"
                
                # Display text on the frame
                cv2.putText(frame, text, (x, y - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                cv2.putText(frame, expiry, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

    # Set expiry date to not update for products not detected
    for product in product_counts:
        if product not in detected_products:
            product_counts[product] = 0  # Reset count if not detected

    return frame

# Initialize video capture
cap = cv2.VideoCapture(0)

# Create a matplotlib figure and axis for displaying frames
plt.ion()  # Enable interactive mode
fig, ax = plt.subplots()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Update expiry dates
    update_expiry_dates()

    # Prepare the frame for YOLO
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    detections = net.forward(output_layers)

    # Draw bounding boxes and update counts
    frame = draw_boxes(frame, detections)

    # Convert frame to RGB (Matplotlib uses RGB)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Clear previous frame and display new frame using matplotlib
    ax.clear()
    ax.imshow(frame_rgb)
    ax.set_title("Smart Agro Storage Detection")
    ax.axis('off')  # Hide axes
    plt.draw()
    plt.pause(0.01)  # Pause to allow for display update

    # Print counts and expiry info to console
    print("Current Counts and Expiry Info:")
    for product, count in product_counts.items():
        expiry = expiry_tracking[product]
        status = "Expired" if expiry <= 0 else f"{expiry} days left"
        print(f"{product}: {count}, Expiry: {status}")

    # Check for exit condition (manual check)
    if plt.waitforbuttonpress(0.1):  # Exit on key press
        break

cap.release()
plt.close()
