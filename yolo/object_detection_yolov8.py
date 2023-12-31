from ultralytics import YOLO
from math import ceil
from time import time
from typer import Typer
from json import load
from cv2 import (
    VideoCapture,
    imshow,
    waitKey,
    VideoWriter,
    putText,
    getTextSize,
    destroyAllWindows,
    rectangle,
    VideoWriter_fourcc,
    FONT_HERSHEY_SIMPLEX,
    FILLED,
)

COLOR_RECTANGLE = (223, 65, 80)[::-1]
COLOR_TEXT = (255, 255, 255)[::-1]
COLOR_OUTLINE = (32, 190, 175)[::-1]

app = Typer()


def init_model(params):
    model = YOLO(params["model"])
    with open(params["coco"], "r") as file:
        classes = file.read().rstrip("\n").split("\n")
    return model, classes


def make_bounding_rectangle(frame, bounding_box, thickness=2, color=COLOR_RECTANGLE):
    if thickness != 0:
        rectangle(frame, bounding_box, color=color, thickness=thickness)
    return frame


def make_text_box(
    frame,
    text,
    pos,
    scale=0.7,
    thickness=2,
    color_text=COLOR_TEXT,
    color_rectangle=COLOR_RECTANGLE,
    font=FONT_HERSHEY_SIMPLEX,
    offset=0,
    border=None,
    color_outline=COLOR_OUTLINE,
):
    ox, oy = pos
    (w, h), _ = getTextSize(text, font, scale, thickness)
    x1, y1, x2, y2 = ox - offset, oy + offset, ox + w + offset, oy - h - offset

    rectangle(frame, (x1, y1), (x2 + 10, y2 - 10), color_rectangle, FILLED)
    if border is not None:
        rectangle(frame, (x1, y1), (x2, y2), color_outline, border)
    putText(frame, text, (ox + 5, oy - 5), font, scale, color_text, thickness)

    return frame, [x1, y2, x2, y1]


def make_annotation(video_capture, model, classes, output_path: str = None):
    prev_frame_time = 0
    new_frame_time = 0
    frame_count = 1

    out = None
    if output_path is not None:
        fourcc = VideoWriter_fourcc(*"mp4v")
        frame_width = int(video_capture.get(3))
        frame_height = int(video_capture.get(4))
        fps = int(video_capture.get(5))
        out = VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

    while True:
        new_frame_time = time()
        success, frame = video_capture.read()

        if not success:
            break
        results = model(frame, stream=True)

        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                w, h = x2 - x1, y2 - y1
                make_bounding_rectangle(frame=frame, bounding_box=(x1, y1, w, h))
                confidence = ceil((box.conf[0] * 100)) / 100
                cls = int(box.cls[0])
                make_text_box(
                    frame, f"{classes[cls]} {confidence}", (max(0, x1), max(35, y1))
                )

        fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time
        print(f"frame_{frame_count}: {fps}")
        frame_count += 1

        imshow("Image", frame)
        if output_path is not None:
            out.write(frame)
        waitKey(1)

    video_capture.release()
    if output_path is not None:
        out.release()
    destroyAllWindows()


@app.command()
def webcam(source: int = 0, params_path: str = "params.json"):
    with open(params_path, "r") as file:
        params = load(file)
    model, classes = init_model(params)
    video_capture = VideoCapture(source)
    video_capture.set(3, 1280)
    video_capture.set(4, 720)
    make_annotation(
        video_capture=video_capture, model=model, classes=classes, output_path=None
    )


@app.command()
def video(path: str, params_path: str = "params.json", output_path: str = None):
    with open(params_path, "r") as file:
        params = load(file)
    model, classes = init_model(params)
    video_capture = VideoCapture(path)
    make_annotation(
        video_capture=video_capture,
        model=model,
        classes=classes,
        output_path=output_path,
    )


if __name__ == "__main__":
    app()
