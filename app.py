import os
import re
import math
from flask import Flask, request, render_template, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'optimized'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files['file']
        if file and file.filename.endswith('.txt'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            output_path = os.path.join(OUTPUT_FOLDER, f"optimized_{filename}")
            optimize_gcode(filepath, output_path)
            return send_file(output_path, as_attachment=True)

    return render_template("index.html")

def optimize_gcode(input_file, output_file):
    with open(input_file, "r") as f:
        lines = f.readlines()

    xy_pattern = re.compile(r"G00 X([-\d.]+)Y([-\d.]+)")
    drill_positions, drill_lines, other_lines = [], [], []

    for i, line in enumerate(lines):
        match = xy_pattern.search(line)
        if match:
            x, y = float(match.group(1)), float(match.group(2))
            drill_positions.append((x, y))
            drill_lines.append((i, line))
        else:
            other_lines.append((i, line))

    def nearest_neighbor(points):
        unvisited = points[:]
        path = [unvisited.pop(0)]
        while unvisited:
            last = path[-1]
            next_point = min(unvisited, key=lambda p: math.hypot(p[0]-last[0], p[1]-last[1]))
            path.append(next_point)
            unvisited.remove(next_point)
        return path

    optimized_order = nearest_neighbor(drill_positions)
    position_to_gcode = {}

    for i in range(len(drill_lines)):
        index = drill_lines[i][0]
        pos = drill_positions[i]
        segment = lines[index:index+4]
        position_to_gcode[pos] = segment

    with open(output_file, "w") as f:
        first_drill_index = drill_lines[0][0]
        for i in range(first_drill_index):
            f.write(lines[i])
        for pos in optimized_order:
            f.writelines(position_to_gcode[pos])
        last_drill_index = drill_lines[-1][0] + 4
        for i in range(last_drill_index, len(lines)):
            f.write(lines[i])

if __name__ == "__main__":
    app.run(debug=True)