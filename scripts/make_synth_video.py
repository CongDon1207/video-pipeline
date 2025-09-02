import cv2
import numpy as np
import os

def main():
    os.makedirs('data', exist_ok=True)
    h, w = 480, 640
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('data/synth.avi', fourcc, 30.0, (w, h))
    for i in range(180):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        x = 50 + (i * 3) % 500
        y = 200
        cv2.rectangle(img, (x, y), (x + 60, y + 100), (0, 255, 0), -1)
        out.write(img)
    out.release()
    print('Wrote data/synth.avi')

if __name__ == '__main__':
    main()

