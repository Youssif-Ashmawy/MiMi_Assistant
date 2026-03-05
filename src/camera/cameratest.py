import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        print("camera failed")
        break

    cv2.imshow("test", frame)

    if cv2.waitKey(1) == 27:
        break