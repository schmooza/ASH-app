"""Teacher-only Turtle engine. Keep in the same folder as student.py."""
import turtle
import math
import random
import os
import tkinter as tk
from sound_effects import start_playlist, stop_playlist, toggle_playlist_audio
from sound_effects import play as play_sound, play_ambient as loop_sound, toggle_sound, is_sound_on, stop as stop_sound, repeat_sound

class Pattern:
    def __init__(self, name="Pattern"):
        self.name = name
        self.count = 1
        self.size_mode = "fixed"
        self.random_colours = False
        self.palette = []
        self.x = 0
        self.y = 0
        self.commands = []

    def repeat(self, count):
        if type(count) is not int or count < 1:
            raise ValueError("Repeat count must be a positive integer")
        self.count = count
        return self

    def grow(self):
        self.size_mode = "grow"
        return self

    def shrink(self):
        self.size_mode = "shrink"
        return self

    def random_colors(self, palette):
        if not palette:
            raise ValueError("Choose at least one colour")
        self.random_colours = True
        self.palette = list(palette)
        return self

    def at(self, x, y):
        if type(x) is not int or type(y) is not int:
            raise ValueError("Pattern coordinates must be integers")
        self.x, self.y = x, y
        return self

    def shape(self, commands):
        self.commands = list(commands)
        return self

    def draw(self):
        if not self.commands:
            raise ValueError("Add shape instructions before draw()")
        result = []
        if self.size_mode == "grow":
            sizes = range(1, self.count + 1)
        elif self.size_mode == "shrink":
            sizes = range(self.count, 0, -1)
        else:
            sizes = [1] * self.count
        for size in sizes:
            result.extend([("up", self.x, self.y), ("heading", 0)])
            if self.random_colours:
                result.append(("random_fill", tuple(self.palette)))
                result.append(("begin_fill",))
            result.append(("down",))
            for command in self.commands:
                if command[0] == "forward" and command[1] == "size":
                    result.append(("forward", size))
                else:
                    result.append(command)
            if self.random_colours:
                result.append(("end_fill",))
            result.append(("up",))
        return result

class Sequence:
    """Collect named drawing events in the order students choose."""
    def __init__(self):
        self.events = []

    def add(self, name, event, sound=None):
        if isinstance(event, Pattern):
            instructions = event.draw()
        else:
            instructions = list(event)
        if sound is not None:
            instructions.insert(0, ("sound", sound))
        # Reset visual styles, but preserve the student's chosen drawing speed.
        instructions = [("color", "black"), ("width", 3)] + instructions
        self.events.append((str(name), instructions))
        return self

    def build(self):
        instructions = []
        for name, event in self.events:
            instructions.extend(event)
        return instructions


# ==========================================
# SHAPE FUNCTIONS - READY FOR STUDENTS
# ==========================================
# Each function returns drawing instructions.
# "size" uses the size chosen by Pattern.grow().

def triangle_shape():
    return [("repeat", 3), ("forward", "size"),
            ("turn", 120), ("end_repeat",)]


def square_shape():
    return [("repeat", 4), ("forward", "size"),
            ("turn", 90), ("end_repeat",)]


def rectangle_shape(width=4, height=2):
    """Return instructions for a rectangle, in grid units.

    Example: Pattern().at(-2, -1).shape(rectangle_shape(4, 2)).draw()
    """
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("Rectangle width and height must be positive whole numbers")
    return [("repeat", 2), ("forward", width), ("turn", 90),
            ("forward", height), ("turn", 90), ("end_repeat",)]


def pentagon_shape():
    return [("repeat", 5), ("forward", "size"),
            ("turn", 72), ("end_repeat",)]


def hexagon_shape():
    return [("repeat", 6), ("forward", "size"),
            ("turn", 60), ("end_repeat",)]


def star_shape():
    return [("repeat", 5), ("forward", "size"),
            ("turn", 144), ("end_repeat",)]


# The following drawing engine is started by student.py.
def start(student_steps, student_colors, background=None):
    global steps, colors, background_choice
    background_choice = background
    steps = list(student_steps)
    colors = list(student_colors)
    run_program()

def run_program():
    global steps, screen, scale, speed, paused, buttons_visible, grid_visible
    global running, step, moving, target_x, target_y, timer_id
    global curve_remaining, curve_radius, curve_direction
    global grid, t, marker, position_text, ui
    def expand_repeats(commands):
        def expand(block, size=None):
            result = []
            i = 0
            while i < len(block):
                command = block[i]
                action = command[0]
                if action in ("repeat", "repeat_grow"):
                    count = command[1]
                    if type(count) is not int or count < 0:
                        raise ValueError("Repeat count must be a non-negative integer")
                    depth = 1
                    j = i + 1
                    while j < len(block) and depth:
                        if block[j][0] in ("repeat", "repeat_grow"):
                            depth += 1
                        elif block[j][0] == "end_repeat":
                            depth -= 1
                        j += 1
                    if depth:
                        raise ValueError("Missing end_repeat")
                    inner = block[i + 1:j - 1]
                    sizes = range(1, count + 1)
                    if len(command) > 2 and command[2] == "largest_first":
                        sizes = range(count, 0, -1)
                    for n in sizes:
                        result.extend(expand(
                            inner, n if action == "repeat_grow" else size))
                    i = j
                elif action == "end_repeat":
                    raise ValueError("end_repeat without repeat")
                elif action == "curve":
                    if len(command) != 3:
                        raise ValueError('Use ("curve", radius, degrees)')
                    radius, degrees = command[1:]
                    if (not isinstance(radius, (int, float)) or isinstance(radius, bool)
                            or radius <= 0 or not isinstance(degrees, (int, float))
                            or isinstance(degrees, bool)):
                        raise ValueError("Curve radius must be positive and angle numeric")
                    if abs(degrees) > 3600:
                        raise ValueError("Curve angle must be at most 3600 degrees")
                    # Keep the curve as one instruction. The animation engine
                    # uses the live image speed for each frame of the arc.
                    result.append(("curve", radius, degrees))
                    i += 1
                else:
                    if action == "forward" and command[1] == "size":
                        if size is None:
                            raise ValueError('Use "size" inside repeat_grow')
                        result.append(("forward", size))
                    else:
                        result.append(command)
                    i += 1
            return result
        return expand(commands)

    steps = expand_repeats(steps)

    screen = turtle.Screen()
    screen.setup(850, 680)
    screen.title("Turtle Name Drawing - Pattern Object")
    screen.tracer(0)
    # Background is a canvas image behind all Turtle drawing and grid items.
    # PNG/GIF work with built-in Tkinter; JPEG works when Pillow is installed.
    canvas = screen.getcanvas()
    background_photo = None
    background_item = None
    if background_choice and background_choice != "none":
        background_path = str(background_choice)
        if not os.path.isabs(background_path):
            if not os.path.splitext(background_path)[1]:
                background_path += ".png"
            background_path = os.path.join(os.path.dirname(__file__),
                                           "backgrounds", background_path)
        if not os.path.isfile(background_path):
            print("Background not found:", background_path)
        else:
            try:
                if background_path.lower().endswith(('.jpg', '.jpeg')):
                    from PIL import Image, ImageTk
                    pic = Image.open(background_path)
                    pic.thumbnail((850, 680))
                    background_photo = ImageTk.PhotoImage(pic, master=canvas)
                else:
                    background_photo = tk.PhotoImage(file=background_path, master=canvas)
                    # Keep very large custom pictures within the classroom window.
                    factor = max(1, math.ceil(background_photo.width()/850),
                                 math.ceil(background_photo.height()/680))
                    if factor > 1:
                        background_photo = background_photo.subsample(factor)
                background_item = canvas.create_image(canvas.canvasx(425), canvas.canvasy(340), image=background_photo)
                canvas.tag_lower(background_item)
            except Exception as exc:
                print("Could not load background:", exc)
    # Keep a Python reference alive while the window is open.
    screen._classroom_background_photo = background_photo

    scale = 38
    speed = 6  # Default image speed; individual commands persist across images
    paused = False
    buttons_visible = True
    grid_visible = True
    running = True
    step = 0
    moving = False
    curve_remaining = 0.0
    curve_radius = 0.0
    curve_direction = 1
    target_x = 0
    target_y = 0
    timer_id = None

    # ------------------------------------------
    # Grid
    # ------------------------------------------

    grid = turtle.Turtle()
    grid.hideturtle()
    grid.speed(0)
    grid.pensize(1)

    def draw_grid():
        grid.clear()
        for n in range(-5, 6):
            grid.color("lightgray")
            grid.penup()
            grid.goto(n * scale, -5 * scale)
            grid.pendown()
            grid.goto(n * scale, 5 * scale)

            grid.penup()
            grid.goto(-5 * scale, n * scale)
            grid.pendown()
            grid.goto(5 * scale, n * scale)

        grid.penup()
        grid.color("black")

        for n in range(-5, 6):
            grid.goto(n * scale, -210)
            grid.write(str(n), align="center",
                       font=("Arial", 10, "normal"))
            grid.goto(-210, n * scale - 5)
            grid.write(str(n), align="center",
                       font=("Arial", 10, "normal"))

        # Highlight axes
        grid.color("gray")
        grid.pensize(2)

        grid.penup()
        grid.goto(-190, 0)
        grid.pendown()
        grid.goto(190, 0)

        grid.penup()
        grid.goto(0, -190)
        grid.pendown()
        grid.goto(0, 190)


    draw_grid()

    # ------------------------------------------
    # Drawing turtle
    # ------------------------------------------

    t = turtle.Turtle()
    t.shape("turtle")
    t.pensize(3)
    t.penup()
    t.speed(0)

    # ------------------------------------------
    # Pause marker
    # ------------------------------------------

    marker = turtle.Turtle()
    marker.hideturtle()
    marker.color("red")
    marker.pensize(2)
    marker.penup()

    position_text = turtle.Turtle()
    position_text.hideturtle()
    position_text.color("red")
    position_text.penup()

    def show_marker():
        marker.clear()
        position_text.clear()

        x = t.xcor()
        y = t.ycor()

        marker.penup()
        marker.goto(x - 10, y)
        marker.pendown()
        marker.goto(x + 10, y)

        marker.penup()
        marker.goto(x, y - 10)
        marker.pendown()
        marker.goto(x, y + 10)
        marker.penup()

        position_text.goto(x + 12, y + 12)
        position_text.write(
            "(" + str(round(x / scale)) +
            ", " + str(round(y / scale)) + ")",
            font=("Arial", 11, "bold")
        )

    # ------------------------------------------
    # Buttons
    # ------------------------------------------

    ui = turtle.Turtle()
    ui.hideturtle()
    ui.speed(0)
    ui.penup()

    def draw_box(x, y, width, colour, text):
        ui.penup()
        ui.goto(x, y)
        ui.setheading(0)
        ui.fillcolor(colour)
        ui.pencolor("black")
        ui.begin_fill()
        ui.pendown()

        for i in range(2):
            ui.forward(width)
            ui.left(90)
            ui.forward(35)
            ui.left(90)

        ui.end_fill()
        ui.penup()
        ui.goto(x + width / 2, y + 10)
        ui.write(text, align="center",
                 font=("Arial", 10, "bold"))

    def show_controls():
        ui.clear()

        if buttons_visible:
            draw_box(-390, 250, 150, "lightblue",
                     "X: " + str(round(t.xcor() / scale)) +
                     " Y: " + str(round(t.ycor() / scale)))

            if paused:
                draw_box(-220, 250, 110, "orange", "RESUME")
            else:
                draw_box(-220, 250, 110, "lightgreen", "PAUSE")

            draw_box(-90, 250, 110, "lightblue", "RESTART")
            draw_box(40, 250, 110, "lightyellow", "SPEED -")
            draw_box(170, 250, 110, "lightyellow", "SPEED +")
            draw_box(300, 250, 90, "salmon", "EXIT")

            draw_box(-105, 202, 210, "lightcyan",
                     "HEADING: " + str(round(t.heading()) % 360) + " degrees")

        # Grid toggle is always visible, even when other buttons are hidden.
        if grid_visible:
            draw_box(-310, -290, 160, "lightgray", "HIDE GRID")
        else:
            draw_box(-310, -290, 160, "lightgreen", "SHOW GRID")

        draw_box(105, -290, 145,
                 "lightgreen" if is_sound_on() else "salmon",
                 "SOUND ON" if is_sound_on() else "SOUND OFF")

        if buttons_visible:
            draw_box(-80, -290, 160,
                     "lightgray", "HIDE BUTTONS")
        else:
            draw_box(-80, -290, 160,
                     "lightgreen", "SHOW BUTTONS")

    # ------------------------------------------
    # Animation timer
    # ------------------------------------------

    def cancel_timer():
        global timer_id

        if timer_id is not None:
            try:
                screen.getcanvas().after_cancel(timer_id)
            except (ValueError, turtle.Terminator):
                pass
            timer_id = None

    def schedule_next():
        global timer_id

        if running and not paused and step < len(steps):
            if timer_id is None:
                # Higher speeds also shorten the frame delay. This makes
                # speed changes obvious for both straight lines and curves.
                delay = 1 if speed == 0 else max(1, round(40 - speed * 0.39))
                timer_id = screen.getcanvas().after(delay, draw_next)

    # ------------------------------------------
    # Button actions
    # ------------------------------------------

    def pause_resume():
        global paused
        paused = not paused

        if paused:
            cancel_timer()
            show_marker()
        else:
            marker.clear()
            position_text.clear()

        show_controls()
        screen.update()

        if not paused:
            schedule_next()

    def restart():
        global step, moving, paused

        cancel_timer()
        stop_playlist()
        stop_sound()
        step = 0
        moving = False
        paused = False

        if t.filling():
            t.end_fill()
        t.clear()
        t.penup()
        t.goto(0, 0)
        t.setheading(0)
        t.fillcolor("black")
        t.showturtle()

        marker.clear()
        position_text.clear()

        show_controls()
        screen.update()
        schedule_next()

    def speed_down():
        global speed
        speed = max(0, speed - 2)
        show_controls()
        screen.update()

    def speed_up():
        global speed
        speed = min(100, speed + 2)
        show_controls()
        screen.update()

    def toggle_buttons():
        global buttons_visible
        buttons_visible = not buttons_visible
        show_controls()
        screen.update()

    def toggle_grid():
        global grid_visible
        grid_visible = not grid_visible
        if grid_visible:
            draw_grid()
        else:
            grid.clear()
        show_controls()
        screen.update()

    def toggle_audio():
        toggle_playlist_audio()
        show_controls()
        screen.update()

    def exit_program():
        global running
        running = False
        cancel_timer()
        stop_playlist()
        stop_sound()
        try:
            screen.bye()
        except turtle.Terminator:
            pass

    def check_click(x, y):
        if 105 <= x <= 250 and -290 <= y <= -255:
            toggle_audio()
            return
        if -310 <= x <= -150 and -290 <= y <= -255:
            toggle_grid()
            return
        if -80 <= x <= 80 and -290 <= y <= -255:
            toggle_buttons()
            return

        if not buttons_visible:
            return

        if 250 <= y <= 285:
            if -220 <= x <= -110:
                pause_resume()
            elif -90 <= x <= 20:
                restart()
            elif 40 <= x <= 150:
                speed_down()
            elif 170 <= x <= 280:
                speed_up()
            elif 300 <= x <= 390:
                exit_program()

    screen.onclick(check_click)
    screen.onkey(pause_resume, "space")
    screen.onkey(toggle_buttons, "h")
    screen.onkey(toggle_grid, "g")
    screen.onkey(toggle_audio, "m")
    screen.onkey(exit_program, "Escape")
    screen.listen()

    # Close safely with the window X button
    screen.getcanvas().winfo_toplevel().protocol(
        "WM_DELETE_WINDOW", exit_program
    )

    # ------------------------------------------
    # Animation using setheading and forward
    # ------------------------------------------

    def draw_next():
        global step, moving, target_x, target_y, speed
        global curve_remaining, curve_radius, curve_direction
        global timer_id

        timer_id = None

        if not running or paused or step >= len(steps):
            return

        # Do not restart an arc while it is being animated.
        if not moving and curve_remaining <= 0:
            instruction = steps[step]
            action = instruction[0]

            if action == "up":
                t.penup()
                if len(instruction) == 3:
                    target_x = instruction[1] * scale
                    target_y = instruction[2] * scale
                    moving = True
                else:
                    step += 1

            elif action == "down":
                t.pendown()
                step += 1

            elif action == "start_playlist":
                start_playlist(instruction[1], screen.getcanvas(), instruction[2] if len(instruction) > 2 else 60)
                step += 1

            elif action == "sound":
                play_sound(instruction[1])
                step += 1

            elif action == "loop_sound":
                loop_sound(instruction[1])
                step += 1

            elif action == "repeat_sound":
                repeat_sound(instruction[1], instruction[2], screen.getcanvas())
                step += 1

            elif action == "stop_sound":
                stop_sound()
                step += 1

            elif action == "random_fill":
                t.fillcolor(random.choice(instruction[1] if len(instruction) > 1 else colors))
                step += 1

            elif action == "speed":
                new_speed = instruction[1]
                if type(new_speed) is not int or not 0 <= new_speed <= 100:
                    raise ValueError("Image speed must be an integer from 0 to 100")
                speed = new_speed
                step += 1

            elif action == "color":
                t.pencolor(instruction[1])
                step += 1

            elif action == "width":
                width = instruction[1]
                if not isinstance(width, (int, float)) or width <= 0:
                    raise ValueError("Pen width must be greater than zero")
                t.pensize(width)
                step += 1

            elif action == "fillcolor":
                t.fillcolor(instruction[1])
                step += 1

            elif action == "begin_fill":
                t.begin_fill()
                step += 1

            elif action == "end_fill":
                t.end_fill()
                step += 1

            elif action == "heading":
                t.setheading(instruction[1])
                step += 1

            elif action == "turn":
                t.left(instruction[1])
                step += 1

            elif action == "curve":
                curve_radius = instruction[1] * scale
                curve_remaining = abs(instruction[2])
                curve_direction = 1 if instruction[2] >= 0 else -1
                if curve_remaining == 0:
                    step += 1

            elif action == "forward":
                target_x = t.xcor() + (
                    instruction[1] * scale *
                    math.cos(
                        math.radians(t.heading())
                    )
                )
                target_y = t.ycor() + (
                    instruction[1] * scale *
                    math.sin(
                        math.radians(t.heading())
                    )
                )
                moving = True

        if curve_remaining > 0:
            # Speed 0 finishes the arc in one frame. For other speeds,
            # allow larger angular steps at higher speeds so curves
            # actually draw faster (rather than hitting a fixed 5-degree cap).
            if speed == 0:
                angle = curve_remaining
            else:
                max_angle = min(90.0, max(2.0, speed * 0.9))
                angle = min(curve_remaining, max_angle,
                            math.degrees(speed / curve_radius))
            signed = angle * curve_direction
            theta = math.radians(t.heading())
            sweep = math.radians(signed)
            # Exact circular arc endpoint from the current tangent.
            dx_arc = curve_radius * (math.sin(theta + sweep) - math.sin(theta)) * curve_direction
            dy_arc = curve_radius * (math.cos(theta) - math.cos(theta + sweep)) * curve_direction
            t.goto(t.xcor() + dx_arc, t.ycor() + dy_arc)
            t.setheading(t.heading() + signed)
            curve_remaining = max(0.0, curve_remaining - angle)
            if curve_remaining < 1e-8:
                curve_remaining = 0.0
                step += 1

        if moving:
            dx = target_x - t.xcor()
            dy = target_y - t.ycor()
            distance = (dx ** 2 + dy ** 2) ** 0.5

            if speed == 0 or distance <= speed:
                t.goto(target_x, target_y)
                moving = False
                step += 1
            else:
                t.goto(
                    t.xcor() + dx / distance * speed,
                    t.ycor() + dy / distance * speed
                )

        if step >= len(steps):
            # Keep the independent music playlist playing after the fast drawing
            # finishes. M toggles music; Esc or closing the window stops it.
            t.hideturtle()

        show_controls()
        screen.update()
        schedule_next()

    # ------------------------------------------
    # Start
    # ------------------------------------------

    show_controls()
    screen.update()
    schedule_next()

    try:
        turtle.done()
    except turtle.Terminator:
        pass
