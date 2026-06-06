__author__ = 'Amir Zahavi'


import pygame
import threading
import traceback
import socket
from send_recv_AES import SendRecvAes
from RSA_mode import RSA
from monster import MonsterSprite


# ── Pygame init ────────────────────────────────────────────────────────────────
pygame.init()
pygame.font.init()

# ── Palette (Bad Ice Cream icy theme) ─────────────────────────────────────────
ICE_BG        = (210, 240, 255)   # very light icy blue background
ICE_PANEL     = (180, 220, 245)   # panel / card color
ICE_DARK      = ( 60, 110, 160)   # dark blue for borders & text
ICE_ACCENT    = ( 30, 180, 220)   # bright cyan accent
ICE_WHITE     = (245, 252, 255)
ICE_SNOW      = (255, 255, 255)
ICE_ERR       = (220,  60,  60)
ICE_OK        = ( 40, 180,  80)
ICE_SHADOW    = (150, 195, 225)
BTN_NORMAL    = ( 90, 190, 230)
BTN_HOVER     = ( 50, 155, 210)
BTN_PRESS     = ( 30, 120, 180)
BTN_TEXT      = (255, 255, 255)
INPUT_BG      = (230, 248, 255)
INPUT_ACTIVE  = (200, 238, 255)
INPUT_BORDER  = (100, 170, 210)
SEE_THROUGH_FRUIT = (63,72,204)
SEE_THROUGH_VANIL = (75,255,142)
SEE_THROUGH_CHOCOLATE = (22,111,240)



# ── Fonts ──────────────────────────────────────────────────────────────────────
def _load_font(size, bold=False):
    # Try a pixel/retro feel; fall back gracefully
    for name in ["Courier New", "Consolas", "monospace"]:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)

FONT_TITLE  = _load_font(38, bold=True)
FONT_BIG    = _load_font(22, bold=True)
FONT_MED    = _load_font(18)
FONT_SMALL  = _load_font(14)
FONT_TINY   = _load_font(12)

W, H = 860, 640
SCREEN = pygame.display.set_mode((W, H))

wall_image = pygame.image.load('wall.png')
ice_image = pygame.image.load('ice.png')
empty_image = pygame.image.load('empty1.png')
special_empty_image = pygame.image.load('empty.png')
fruit_image = pygame.image.load('fruit.png').convert()
fruit_image.set_colorkey(SEE_THROUGH_FRUIT)


def load_sprite_sheet(path, frame_w, frame_h, scale=1):
    sheet = pygame.image.load(path).convert()
    sheet.set_colorkey(sheet.get_at((0, 0)))
    frames = []
    cols = sheet.get_width() // frame_w
    for i in range(cols):
        frame = sheet.subsurface((i * frame_w, 0, frame_w, frame_h))
        if scale != 1:
            frame = pygame.transform.scale(frame,
                                           (frame_w * scale, frame_h * scale))
        frames.append(frame)
    return frames

blue_walk_frames_r = load_sprite_sheet('blue_walk.png', 32, 32)
blue_walk_frames_l = [pygame.transform.flip(f, True, False) for f in blue_walk_frames_r]

white_walk_frames_r = load_sprite_sheet('white_walk.png', 32, 32)
white_walk_frames_l = [pygame.transform.flip(f, True, False) for f in white_walk_frames_r]

monster_frames = load_sprite_sheet('SnowManIdle.png', 16, 16, scale=2)

_TILE_SIZE = 32


pygame.display.set_caption("❄  Bad Ice Cream — Multiplayer Client")

CLOCK = pygame.time.Clock()

# ── Snowflake particles ────────────────────────────────────────────────────────
import random, math

class Snowflake:
    def __init__(self):
        self.reset(initial=True)

    def reset(self, initial=False):
        self.x = random.randint(0, W)
        self.y = random.randint(0, H) if initial else -8
        self.r = random.uniform(2, 5)
        self.speed = random.uniform(0.4, 1.2)
        self.drift = random.uniform(-0.3, 0.3)
        self.alpha = random.randint(120, 200)

    def update(self):
        self.y += self.speed
        self.x += self.drift
        if self.y > H + 8:
            self.reset()

    def draw(self, surf):
        s = pygame.Surface((int(self.r*2+2), int(self.r*2+2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*ICE_WHITE, self.alpha), (int(self.r+1), int(self.r+1)), int(self.r))
        surf.blit(s, (int(self.x - self.r), int(self.y - self.r)))

SNOWFLAKES = [Snowflake() for _ in range(55)]

# ── Utility drawing helpers ────────────────────────────────────────────────────

def draw_bg(surf):
    surf.fill(ICE_BG)
    # subtle gradient bands
    for i in range(H):
        ratio = i / H
        r = int(210 + 20 * ratio)
        g = int(240 - 10 * ratio)
        b = 255
        pygame.draw.line(surf, (r, g, b), (0, i), (W, i))
    for flake in SNOWFLAKES:
        flake.update()
        flake.draw(surf)

def draw_panel(surf, rect, radius=14):
    x, y, w, h = rect
    # shadow
    sr = pygame.Rect(x+4, y+4, w, h)
    pygame.draw.rect(surf, ICE_SHADOW, sr, border_radius=radius)
    # main panel
    pygame.draw.rect(surf, ICE_PANEL, rect, border_radius=radius)
    pygame.draw.rect(surf, ICE_DARK, rect, width=2, border_radius=radius)

def draw_text(surf, text, font, color, cx, cy, anchor="center"):
    img = font.render(text, True, color)
    r = img.get_rect()
    if anchor == "center":
        r.center = (cx, cy)
    elif anchor == "left":
        r.midleft = (cx, cy)
    elif anchor == "right":
        r.midright = (cx, cy)
    surf.blit(img, r)
    return r

def draw_title(surf):
    # ice-block style title
    title = "❄  BAD ICE CREAM  ❄"
    img = FONT_TITLE.render(title, True, ICE_DARK)
    r = img.get_rect(center=(W//2, 38))
    # shadow
    sh = FONT_TITLE.render(title, True, ICE_SHADOW)
    surf.blit(sh, (r.x+2, r.y+2))
    surf.blit(img, r)

# ── Button ─────────────────────────────────────────────────────────────────────

class Button:
    def __init__(self, rect, text, font=None, color=BTN_NORMAL, text_color=BTN_TEXT):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font or FONT_MED
        self.color = color
        self.text_color = text_color
        self._hover = False
        self._pressed = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True
                return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._pressed = False
        return False

    def draw(self, surf):
        col = BTN_PRESS if self._pressed else (BTN_HOVER if self._hover else self.color)
        pygame.draw.rect(surf, col, self.rect, border_radius=8)
        pygame.draw.rect(surf, ICE_DARK, self.rect, width=2, border_radius=8)
        draw_text(surf, self.text, self.font, self.text_color, self.rect.centerx, self.rect.centery)

# ── Input field ────────────────────────────────────────────────────────────────

class InputField:
    def __init__(self, rect, placeholder="", password=False, font=None, max_len=40):
        self.rect = pygame.Rect(rect)
        self.placeholder = placeholder
        self.password = password
        self.font = font or FONT_MED
        self.max_len = max_len
        self.text = ""
        self.active = False
        self._cursor_tick = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_TAB:
                pass  # handled by screen
            elif event.unicode and len(self.text) < self.max_len:
                if event.unicode.isprintable():
                    self.text += event.unicode

    def draw(self, surf):
        bg = INPUT_ACTIVE if self.active else INPUT_BG
        pygame.draw.rect(surf, bg, self.rect, border_radius=6)
        border_col = ICE_ACCENT if self.active else INPUT_BORDER
        pygame.draw.rect(surf, border_col, self.rect, width=2, border_radius=6)
        display = ("•" * len(self.text)) if self.password else self.text
        if display:
            draw_text(surf, display, self.font, ICE_DARK, self.rect.x + 10, self.rect.centery, anchor="left")
        elif not self.active:
            draw_text(surf, self.placeholder, self.font, ICE_SHADOW, self.rect.x + 10, self.rect.centery, anchor="left")
        # cursor
        if self.active:
            self._cursor_tick += 1
            if (self._cursor_tick // 30) % 2 == 0:
                tw = self.font.size(display)[0]
                cx = self.rect.x + 10 + tw + 2
                cy1 = self.rect.centery - 9
                cy2 = self.rect.centery + 9
                pygame.draw.line(surf, ICE_DARK, (cx, cy1), (cx, cy2), 2)

# ── Message log (scrollable) ───────────────────────────────────────────────────

class MessageLog:
    def __init__(self, rect, font=None):
        self.rect = pygame.Rect(rect)
        self.font = font or FONT_SMALL
        self.messages = []
        self.scroll = 0

    def add(self, text, color=ICE_DARK):
        self.messages.append((text, color))
        # auto-scroll to bottom
        self.scroll = max(0, len(self.messages) - self._visible_lines())

    def _visible_lines(self):
        return self.rect.height // (self.font.get_height() + 2)

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll = max(0, min(self.scroll - event.y, max(0, len(self.messages) - self._visible_lines())))

    def draw(self, surf):
        pygame.draw.rect(surf, INPUT_BG, self.rect, border_radius=6)
        pygame.draw.rect(surf, INPUT_BORDER, self.rect, width=2, border_radius=6)
        lh = self.font.get_height() + 2
        visible = self._visible_lines()
        clip = surf.get_clip()
        surf.set_clip(self.rect)
        for i, (msg, col) in enumerate(self.messages[self.scroll: self.scroll + visible]):
            y = self.rect.y + 4 + i * lh
            img = self.font.render(msg, True, col)
            surf.blit(img, (self.rect.x + 6, y))
        surf.set_clip(clip)



# ══════════════════════════════════════════════════════════════════════════════
#  SCREENS
# ══════════════════════════════════════════════════════════════════════════════

class Screen:
    """Base class for all screens."""
    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        pass

    def update(self):
        pass

    def draw(self, surf):
        draw_bg(surf)
        draw_title(surf)

# ── Connect Screen ─────────────────────────────────────────────────────────────

class ConnectScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        cx = W // 2
        self.msg = ""
        self.msg_color = ICE_ERR

        self.ip_field    = InputField((cx-140, 200, 280, 36), placeholder="Server IP (127.0.0.1)")
        self.port_field  = InputField((cx-140, 252, 280, 36), placeholder="Port (4010)")
        self.port_field.text = "4010"
        self.ip_field.text   = "127.0.0.1"

        self.fields = [self.ip_field, self.port_field]
        self.btn_connect = Button((cx-90, 310, 180, 40), "Connect  ❄")

    def handle_event(self, event):
        for f in self.fields:
            f.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            idx = next((i for i,f in enumerate(self.fields) if f.active), -1)
            for f in self.fields: f.active = False
            self.fields[(idx+1) % len(self.fields)].active = True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._connect()
        if self.btn_connect.handle_event(event):
            self._connect()

    def _connect(self):
        ip = self.ip_field.text.strip() or "127.0.0.1"
        try:
            port = int(self.port_field.text.strip() or "4010")
        except ValueError:
            self.msg = "Invalid port!"; self.msg_color = ICE_ERR; return
        try:
            self.app.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.app.sock.connect((ip, port))
            self.app.connected = True
            self.app.send_recv_AES = SendRecvAes(self.app.sock)
            # always RSA (DH removed)
            self.app.rsa_mode = RSA(self.app.sock)
            self.app.rsa_mode.ask_for_public_key()
            self.app.mode_stage = "RSA"
            self.app.start_listener()
            self.app.set_screen("login")
        except Exception as e:
            self.msg = str(e)[:60]; self.msg_color = ICE_ERR

    def draw(self, surf):
        super().draw(surf)
        cx = W // 2
        draw_panel(surf, (cx-200, 170, 400, 220))
        draw_text(surf, "Connect to Server", FONT_BIG, ICE_DARK, cx, 185)
        draw_text(surf, "IP Address", FONT_SMALL, ICE_DARK, cx-140, 192, anchor="left")
        self.ip_field.draw(surf)
        draw_text(surf, "Port", FONT_SMALL, ICE_DARK, cx-140, 244, anchor="left")
        self.port_field.draw(surf)
        self.btn_connect.draw(surf)
        if self.msg:
            draw_text(surf, self.msg, FONT_SMALL, self.msg_color, cx, 365)

    def update(self):
        self.btn_connect._hover = self.btn_connect.rect.collidepoint(pygame.mouse.get_pos())

# ── Login Screen ───────────────────────────────────────────────────────────────

class LoginScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        cx = W // 2
        self.msg = ""
        self.msg_color = ICE_ERR

        self.user_field = InputField((cx-140, 200, 280, 36), placeholder="Username")
        self.pass_field = InputField((cx-140, 252, 280, 36), placeholder="Password", password=True)
        self.fields = [self.user_field, self.pass_field]

        self.btn_login  = Button((cx-155, 310, 140, 38), "Login")
        self.btn_signup = Button((cx+15,  310, 140, 38), "Sign Up")
        self.btn_forgot = Button((cx-80,  362, 160, 32), "Forgot Password?",
                                  font=FONT_SMALL, color=ICE_SHADOW, text_color=ICE_DARK)

    def handle_event(self, event):
        for f in self.fields: f.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            idx = next((i for i,f in enumerate(self.fields) if f.active), -1)
            for f in self.fields: f.active = False
            self.fields[(idx+1) % len(self.fields)].active = True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._login()
        if self.btn_login.handle_event(event):  self._login()
        if self.btn_signup.handle_event(event): self.app.set_screen("signup")
        if self.btn_forgot.handle_event(event): self._forgot()

    def set_msg(self, text, ok=False):
        self.msg = text
        self.msg_color = ICE_OK if ok else ICE_ERR

    def _login(self):
        u = self.user_field.text.strip()
        p = self.pass_field.text.strip()
        if not u or not p:
            self.set_msg("Please fill in both fields."); return
        self.app._pending_username = u
        self.app.send_message(f"LGN~{u}~{p}")

    def _forgot(self):
        u = self.user_field.text.strip()
        if not u:
            self.set_msg("Enter your username first."); return
        self.app._forgot_username = u
        self.app.send_message(f"FGP~{u}")
        self.app.set_screen("verify", next_action="forgot", username=u)

    def draw(self, surf):
        super().draw(surf)
        cx = W // 2
        draw_panel(surf, (cx-210, 165, 420, 250))
        draw_text(surf, "Login", FONT_BIG, ICE_DARK, cx, 182)
        draw_text(surf, "Username", FONT_SMALL, ICE_DARK, cx-140, 192, anchor="left")
        self.user_field.draw(surf)
        draw_text(surf, "Password", FONT_SMALL, ICE_DARK, cx-140, 244, anchor="left")
        self.pass_field.draw(surf)
        self.btn_login.draw(surf)
        self.btn_signup.draw(surf)
        self.btn_forgot.draw(surf)
        if self.msg:
            col = ICE_OK if self.msg_color == ICE_OK else ICE_ERR
            draw_text(surf, self.msg, FONT_SMALL, col, cx, 408)

# ── Signup Screen ──────────────────────────────────────────────────────────────

class SignupScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        cx = W // 2
        self.msg = ""
        self.msg_color = ICE_ERR

        y0 = 155
        dy = 52
        self.first_field = InputField((cx-140, y0,       280, 34), placeholder="First Name")
        self.last_field  = InputField((cx-140, y0+dy,    280, 34), placeholder="Last Name")
        self.email_field = InputField((cx-140, y0+dy*2,  280, 34), placeholder="Email")
        self.phone_field = InputField((cx-140, y0+dy*3,  280, 34), placeholder="Phone")
        self.user_field  = InputField((cx-140, y0+dy*4,  280, 34), placeholder="Username")
        self.pass_field  = InputField((cx-140, y0+dy*5,  280, 34), placeholder="Password", password=True)
        self.fields = [self.first_field, self.last_field, self.email_field,
                       self.phone_field, self.user_field, self.pass_field]

        self.btn_submit = Button((cx-155, y0+dy*6+4, 140, 38), "Sign Up")
        self.btn_back   = Button((cx+15,  y0+dy*6+4, 140, 38), "Back",
                                  color=ICE_SHADOW, text_color=ICE_DARK)

    def handle_event(self, event):
        for f in self.fields: f.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            idx = next((i for i,f in enumerate(self.fields) if f.active), -1)
            for f in self.fields: f.active = False
            self.fields[(idx+1) % len(self.fields)].active = True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._submit()
        if self.btn_submit.handle_event(event): self._submit()
        if self.btn_back.handle_event(event):   self.app.set_screen("login")

    def set_msg(self, text, ok=False):
        self.msg = text
        self.msg_color = ICE_OK if ok else ICE_ERR

    def _submit(self):
        first = self.first_field.text.strip()
        last  = self.last_field.text.strip()
        email = self.email_field.text.strip()
        phone = self.phone_field.text.strip()
        user  = self.user_field.text.strip()
        pw    = self.pass_field.text.strip()
        if not all([first, last, email, phone, user, pw]):
            self.set_msg("Please fill in all fields."); return
        # save for verify screen
        self.app._pending_username = user
        self.app._pending_password = pw
        msg = f"SNP~{user}~{pw}~{first}:{last}:{email}:{phone}"
        self.app.send_message(msg)

    def draw(self, surf):
        super().draw(surf)
        cx = W // 2
        labels = ["First Name", "Last Name", "Email", "Phone", "Username", "Password"]
        y0 = 155; dy = 52
        draw_panel(surf, (cx-210, 130, 420, dy*6+80))
        draw_text(surf, "Sign Up", FONT_BIG, ICE_DARK, cx, 143)
        for i, (lbl, fld) in enumerate(zip(labels, self.fields)):
            draw_text(surf, lbl, FONT_SMALL, ICE_DARK, cx-140, y0+dy*i-10, anchor="left")
            fld.draw(surf)
        self.btn_submit.draw(surf)
        self.btn_back.draw(surf)
        if self.msg:
            draw_text(surf, self.msg, FONT_TINY, self.msg_color, cx, y0+dy*6+52)

# ── Verify Code Screen ─────────────────────────────────────────────────────────

class VerifyScreen(Screen):
    """Used for signup email verify AND forgot-password verify."""
    def __init__(self, app, next_action="signup", username=""):
        super().__init__(app)
        self.next_action = next_action  # "signup" or "forgot"
        self.username = username
        cx = W // 2
        self.msg = ""
        self.code_field = InputField((cx-60, 230, 120, 42), placeholder="0000", font=FONT_BIG, max_len=4)
        self.code_field.active = True
        self.btn_confirm   = Button((cx-130, 296, 120, 38), "Confirm")
        self.btn_resend    = Button((cx+10,  296, 120, 38), "Resend", color=ICE_SHADOW, text_color=ICE_DARK)

    def set_msg(self, text, ok=False):
        self.msg = text
        self._msg_ok = ok

    def handle_event(self, event):
        self.code_field.handle_event(event)
        # only allow digits
        if event.type == pygame.KEYDOWN and self.code_field.active:
            if event.unicode and not event.unicode.isdigit():
                self.code_field.text = self.code_field.text  # block non-digit (already added in InputField, undo)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._confirm()
        if self.btn_confirm.handle_event(event): self._confirm()
        if self.btn_resend.handle_event(event):  self._resend()

    def _confirm(self):
        code = self.code_field.text.strip()
        if len(code) != 4:
            self.msg = "Enter exactly 4 digits."; return
        if self.next_action == "signup":
            self.app.send_message(f"SP2~{code}")
        else:
            self.app.send_message(f"CKP~{code}")

    def _resend(self):
        self.app.send_message("SAG")
        self.msg = "New code sent!"

    def draw(self, surf):
        super().draw(surf)
        cx = W // 2
        draw_panel(surf, (cx-200, 178, 400, 185))
        draw_text(surf, "Email Verification", FONT_BIG, ICE_DARK, cx, 196)
        draw_text(surf, "Enter the 4-digit code sent to your email", FONT_SMALL, ICE_DARK, cx, 222)
        self.code_field.draw(surf)
        self.btn_confirm.draw(surf)
        self.btn_resend.draw(surf)
        if self.msg:
            col = ICE_OK if getattr(self, '_msg_ok', False) else ICE_ERR
            draw_text(surf, self.msg, FONT_SMALL, col, cx, 348)

# ── New Password Screen ────────────────────────────────────────────────────────

class NewPasswordScreen(Screen):
    def __init__(self, app, username=""):
        super().__init__(app)
        self.username = username
        cx = W // 2
        self.msg = ""
        self.pass1 = InputField((cx-140, 220, 280, 36), placeholder="New Password", password=True)
        self.pass2 = InputField((cx-140, 272, 280, 36), placeholder="Confirm Password", password=True)
        self.fields = [self.pass1, self.pass2]
        self.btn_ok = Button((cx-70, 328, 140, 38), "Set Password")

    def set_msg(self, text, ok=False):
        self.msg = text; self._ok = ok

    def handle_event(self, event):
        for f in self.fields: f.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            idx = next((i for i,f in enumerate(self.fields) if f.active), -1)
            for f in self.fields: f.active = False
            self.fields[(idx+1) % len(self.fields)].active = True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN: self._submit()
        if self.btn_ok.handle_event(event): self._submit()

    def _submit(self):
        p1 = self.pass1.text.strip()
        p2 = self.pass2.text.strip()
        if not p1:
            self.set_msg("Enter a password."); return
        if p1 != p2:
            self.set_msg("Passwords don't match."); return
        self.app.send_message(f"NWP~{p1}~{self.username}")
        self.set_msg("Password updated! Please log in.", ok=True)
        pygame.time.set_timer(pygame.USEREVENT + 10, 1500)

    def draw(self, surf):
        super().draw(surf)
        cx = W // 2
        draw_panel(surf, (cx-210, 188, 420, 210))
        draw_text(surf, "Reset Password", FONT_BIG, ICE_DARK, cx, 206)
        draw_text(surf, "New Password", FONT_SMALL, ICE_DARK, cx-140, 212, anchor="left")
        self.pass1.draw(surf)
        draw_text(surf, "Confirm Password", FONT_SMALL, ICE_DARK, cx-140, 264, anchor="left")
        self.pass2.draw(surf)
        self.btn_ok.draw(surf)
        if self.msg:
            col = ICE_OK if getattr(self, '_ok', False) else ICE_ERR
            draw_text(surf, self.msg, FONT_SMALL, col, cx, 380)


class EndScreen:
    def __init__(self, result):
        self.result = result
        # Create fonts for the results display
        self.title_font = pygame.font.SysFont("Arial", 60, bold=True)
        self.msg_font = pygame.font.SysFont("Arial", 30)
        self.sub_font = pygame.font.SysFont("Arial", 22, italic=True)

    def handle_event(self, event):
        pass  # Ignore keyboard/mouse inputs during the game-over screen

    def update(self):
        pass  # No physics or animations needed here

    def draw(self, screen):
        # 1. Fill the entire window with an icy blue background
        screen.fill((210, 240, 255))

        # 2. Render text based on win or lose status
        if self.result == 'win':
            title_text = self.title_font.render("🏆 VICTORY 🏆", True, (40, 180, 80))  # Green
            msg_text = self.msg_font.render("All fruits collected successfully!", True, (60, 110, 160))
        else:
            title_text = self.title_font.render("💀 DEFEAT 💀", True, (220, 60, 60))  # Red
            msg_text = self.msg_font.render("The monsters caught you!", True, (60, 110, 160))

        countdown_text = self.sub_font.render("Closing game and disconnecting in 4 seconds...", True, (120, 140, 160))

        # 3. Calculate center positions for all text layers
        w, h = screen.get_width(), screen.get_height()
        title_rect = title_text.get_rect(center=(w // 2, h // 2 - 60))
        msg_rect = msg_text.get_rect(center=(w // 2, h // 2 + 10))
        count_rect = countdown_text.get_rect(center=(w // 2, h // 2 + 80))

        # 4. Draw the text layers onto the screen
        screen.blit(title_text, title_rect)
        screen.blit(msg_text, msg_rect)
        screen.blit(countdown_text, count_rect)

class MainScreen(Screen):
    # Layout constants
    CHAT_H      = 180   # height of the bottom chat strip
    MAP_MARGIN  = 8     # gap around the map placeholder
    MAP_TOP     = 10    # y start (no title bar on this screen)

    def __init__(self, app):
        super().__init__(app)

        # geometry
        map_bottom  = H - self.CHAT_H - self.MAP_MARGIN
        map_rect    = (self.MAP_MARGIN, self.MAP_TOP,
                       W - self.MAP_MARGIN * 2, map_bottom - self.MAP_TOP)

        chat_y      = H - self.CHAT_H
        log_rect    = (self.MAP_MARGIN, chat_y + 32,
                       W - self.MAP_MARGIN * 2, self.CHAT_H - 72)
        input_y     = H - 36

        self.move_cooldown = 0

        self.got_first_upd = False

        self.anim_frame_1 = 0
        self.anim_frame_2 = 0
        self.anim_tick_1 = 0
        self.anim_tick_2 = 0
        self.player1_hdir = 'R'
        self.player2_hdir = 'R'

        self.player1_alive = True
        self.player2_alive = True
        self.grid = [['E'] * 26 for _ in range(14)]
        self.my_player_num = 0
        self.player1 = ()
        self.player1_pixel = ()
        self.player2 = ()
        self.player2_pixel = ()
        self.monsters = []
        self.scores = []

        self.monster_group = pygame.sprite.Group()

        self._map_rect  = pygame.Rect(map_rect)
        self._chat_rect = pygame.Rect(self.MAP_MARGIN, chat_y,
                                      W - self.MAP_MARGIN * 2, self.CHAT_H)

        self.log        = MessageLog(log_rect)
        self.msg_field  = InputField((self.MAP_MARGIN, input_y,
                                      W - self.MAP_MARGIN * 2 - 120, 30),
                                     placeholder="Type a message and press Enter…",
                                     font=FONT_SMALL)
        self.msg_field.active = False
        self.btn_send   = Button((W - self.MAP_MARGIN - 112, input_y, 54, 30),
                                  "Send", font=FONT_SMALL)
        self.btn_disc   = Button((W - self.MAP_MARGIN - 54,  input_y, 54, 30),
                                  "Exit", font=FONT_SMALL, color=ICE_ERR)

        # teammate (filled in by ClientGUI._update_users)
        self.teammate   = ""

        # ice-crystal decoration points for map placeholder
        self._crystals  = self._gen_crystals()
        self.special_tiles = set()
        for row in range(14):
            for col in range(26):
                if random.randint(1, 12) == 1:
                    self.special_tiles.add((row, col))

    # ── decorative ice crystals for the empty map ──────────────────────────────
    @staticmethod
    def _gen_crystals():
        import random
        rng = random.Random(42)
        crystals = []
        for _ in range(18):
            x = rng.randint(60, W - 60)
            y = rng.randint(40, H - 220)
            size = rng.randint(12, 30)
            alpha = rng.randint(60, 140)
            crystals.append((x, y, size, alpha))
        return crystals

    def set_upd_argvs(self, upd_data):
        self.scores = []
        parts = upd_data.decode().split('~')

        p_parts = parts[0].split(',')
        new_p1 = (int(p_parts[0]), int(p_parts[1]), p_parts[3])
        self.scores.append(int(p_parts[2]))
        if not self.got_first_upd:
            self.player1_pixel = [new_p1[0] * _TILE_SIZE, new_p1[1] * _TILE_SIZE]
        self.player1 = new_p1

        p_parts = parts[1].split(',')
        new_p2 = (int(p_parts[0]), int(p_parts[1]), p_parts[3])
        self.scores.append(int(p_parts[2]))
        if not self.got_first_upd:
            self.player2_pixel = [new_p2[0] * _TILE_SIZE, new_p2[1] * _TILE_SIZE]
            self.got_first_upd = True
        self.player2 = new_p2

        if self.player1[2] in ('L', 'R'):
            self.player1_hdir = self.player1[2]
        if self.player2[2] in ('L', 'R'):
            self.player2_hdir = self.player2[2]

        # ── monsters ──
        monster_data = [m for m in parts[2].split(':') if m]
        sprites = self.monster_group.sprites()

        if len(sprites) == 0:
            # first time — create all monster sprites
            for m in monster_data:
                col, row = int(m.split(',')[0]), int(m.split(',')[1])
                sprite = MonsterSprite(monster_frames, col, row,
                                       _TILE_SIZE, self._map_rect)
                self.monster_group.add(sprite)
        else:
            # update targets for existing sprites
            for i, m in enumerate(monster_data):
                if i >= len(sprites):
                    break
                col, row = int(m.split(',')[0]), int(m.split(',')[1])
                sprites[i].set_target(col, row)

        # ── tile changes ──
        tiles = parts[3].split(':')
        for t in tiles:
            if not t:
                continue
            t_parts = t.split(',')
            self.grid[int(t_parts[1])][int(t_parts[0])] = t_parts[2]

    def _draw_map(self, surf):
        for row_idx, row in enumerate(self.grid):
            for col_idx, char in enumerate(row):
                x = self._map_rect.x + col_idx * _TILE_SIZE
                y = self._map_rect.y + row_idx * _TILE_SIZE
                if char == 'I':
                    surf.blit(ice_image, (x, y))
                elif char == 'W':
                    surf.blit(wall_image, (x, y))
                else:
                    if (row_idx, col_idx) in self.special_tiles:
                        surf.blit(special_empty_image, (x, y))
                    else:
                        surf.blit(empty_image, (x, y))
                    if char == 'F':
                        surf.blit(fruit_image, (x, y))

        # ── score ──
        if len(self.scores) >= 1:
            my_score = self.scores[self.my_player_num - 1] if self.my_player_num in (1, 2) else 0
            score_txt = FONT_BIG.render(f"Score: {my_score}", True, (255, 230, 50))
            tx = self._map_rect.right - 6
            ty = self._map_rect.top + 16
            text_rect = score_txt.get_rect(midright=(tx, ty))
            bg_rect = text_rect.inflate(12, 6)
            pygame.draw.rect(surf, (20, 20, 50), bg_rect, border_radius=6)
            surf.blit(score_txt, text_rect)

        # ── monsters ──
        self.monster_group.draw(surf)

        # ── player 1 ──
        if self.player1 and self.player1_pixel:
            x = self._map_rect.x + self.player1_pixel[0]
            y = self._map_rect.y + self.player1_pixel[1]
            if self.player1_hdir == 'R':
                surf.blit(blue_walk_frames_r[self.anim_frame_1], (x, y))
            else:
                surf.blit(blue_walk_frames_l[self.anim_frame_1], (x, y))

        # ── player 2 ──
        if self.player2 and self.player2_pixel:
            x = self._map_rect.x + self.player2_pixel[0]
            y = self._map_rect.y + self.player2_pixel[1]
            if self.player2_hdir == 'R':
                surf.blit(white_walk_frames_r[self.anim_frame_2], (x, y))
            else:
                surf.blit(white_walk_frames_l[self.anim_frame_2], (x, y))




    #def _draw_map_placeholder(self, surf):
    #    # dark icy background
    #    MAP_BG   = ( 30,  70, 120)
    #    MAP_GRID = ( 45,  90, 140)
    #    MAP_ICE  = (120, 200, 240)
#
    #    pygame.draw.rect(surf, MAP_BG, self._map_rect, border_radius=12)
    #    pygame.draw.rect(surf, ICE_DARK, self._map_rect, width=3, border_radius=12)
#
    #    # subtle grid
    #    clip = surf.get_clip()
    #    surf.set_clip(self._map_rect)
    #    cell = 40
    #    for gx in range(self._map_rect.left, self._map_rect.right, cell):
    #        pygame.draw.line(surf, MAP_GRID, (gx, self._map_rect.top),
    #                         (gx, self._map_rect.bottom), 1)
    #    for gy in range(self._map_rect.top, self._map_rect.bottom, cell):
    #        pygame.draw.line(surf, MAP_GRID, (self._map_rect.left, gy),
    #                         (self._map_rect.right, gy), 1)
#
    #    # floating ice crystal shapes
    #    for (cx, cy, size, alpha) in self._crystals:
    #        s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
    #        # hexagon-ish crystal: draw 3 lines through center
    #        import math
    #        for angle in (0, 60, 120):
    #            rad = math.radians(angle)
    #            dx = int(math.cos(rad) * size)
    #            dy = int(math.sin(rad) * size)
    #            pygame.draw.line(s, (*MAP_ICE, alpha),
    #                             (size - dx, size - dy),
    #                             (size + dx, size + dy), 2)
    #        pygame.draw.circle(s, (*MAP_ICE, alpha), (size, size), 3)
    #        surf.blit(s, (cx - size, cy - size))
#
    #    surf.set_clip(clip)
#
    #    # centre label
    #    cx = self._map_rect.centerx
    #    cy = self._map_rect.centery
    #    lbl1 = FONT_BIG.render("❄  GAME MAP  ❄", True, (160, 220, 255))
    #    lbl2 = FONT_SMALL.render("(coming soon…)", True, (100, 160, 210))
    #    surf.blit(lbl1, lbl1.get_rect(center=(cx, cy - 14)))
    #    surf.blit(lbl2, lbl2.get_rect(center=(cx, cy + 16)))

    def _draw_chat_strip(self, surf):
        # panel background
        pygame.draw.rect(surf, ICE_PANEL, self._chat_rect, border_radius=10)
        pygame.draw.rect(surf, ICE_DARK,  self._chat_rect, width=2, border_radius=10)

        # header bar
        header_rect = pygame.Rect(self._chat_rect.x, self._chat_rect.y,
                                  self._chat_rect.width, 28)
        pygame.draw.rect(surf, ICE_DARK, header_rect,
                         border_top_left_radius=10, border_top_right_radius=10)

        if self.teammate:
            header_txt = f"💬  Chat with  {self.teammate}"
        else:
            header_txt = "💬  Chat  —  waiting for teammate…"
        draw_text(surf, header_txt, FONT_SMALL, ICE_WHITE,
                  self._chat_rect.centerx, self._chat_rect.y + 14)

    # ── event / send ──────────────────────────────────────────────────────────
    def handle_event(self, event):
        self.msg_field.handle_event(event)
        self.log.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._send()
        if self.btn_send.handle_event(event): self._send()
        if self.btn_disc.handle_event(event): self.app.disconnect()

    def player_die(self, num):
        if num == 1:
            self.player1_alive = False
        else:
            self.player2_alive = False
        return



    def update(self):
        if self.teammate == "":
            return

        # ── monster animation & movement ──
        self.monster_group.update()

        # ── animation player 1 ──
        if self.player1 and self.player1_pixel:
            target_x = self.player1[0] * _TILE_SIZE
            target_y = self.player1[1] * _TILE_SIZE
            moving1 = (self.player1_pixel[0] != target_x or self.player1_pixel[1] != target_y)
            if moving1:
                self._anim_tick_1 += 1
                if self._anim_tick_1 >= 6:
                    self._anim_tick_1 = 0
                    self.anim_frame_1 = (self.anim_frame_1 + 1) % len(blue_walk_frames_r)
            else:
                self.anim_frame_1 = 0
                self._anim_tick_1 = 0

        # ── animation player 2 ──
        if self.player2 and self.player2_pixel:
            target_x = self.player2[0] * _TILE_SIZE
            target_y = self.player2[1] * _TILE_SIZE
            moving2 = (self.player2_pixel[0] != target_x or self.player2_pixel[1] != target_y)
            if moving2:
                self._anim_tick_2 += 1
                if self._anim_tick_2 >= 6:
                    self._anim_tick_2 = 0
                    self.anim_frame_2 = (self.anim_frame_2 + 1) % len(white_walk_frames_r)
            else:
                self.anim_frame_2 = 0
                self._anim_tick_2 = 0

        # ── movement cooldown ──
        self.move_cooldown -= 1
        if self.move_cooldown > 0:
            return

        if self.my_player_num == 1 and not self.player1_alive:
            return
        if self.my_player_num == 2 and not self.player2_alive:
            return

        keys = pygame.key.get_pressed()
        direction = None

        if keys[pygame.K_UP]:
            direction = 'U'
        elif keys[pygame.K_DOWN]:
            direction = 'D'
        elif keys[pygame.K_LEFT]:
            direction = 'L'
        elif keys[pygame.K_RIGHT]:
            direction = 'R'

        if direction:
            self.app.send_message(f"MOV~{direction}")
            if self.my_player_num == 1:
                self.player1 = (self.player1[0], self.player1[1], direction)
                if direction in ('L', 'R'):
                    self.player1_hdir = direction
            elif self.my_player_num == 2:
                self.player2 = (self.player2[0], self.player2[1], direction)
                if direction in ('L', 'R'):
                    self.player2_hdir = direction
            self.move_cooldown = 10

        if keys[pygame.K_SPACE] and not self.msg_field.active and self.move_cooldown < -10:
            self.move_cooldown = 10
            if self.my_player_num == 1 and self.player1:
                facing = self.player1[2]
            elif self.my_player_num == 2 and self.player2:
                facing = self.player2[2]
            else:
                facing = None
            if facing:
                self.app.send_message(f"SPW~{facing}")

    def _send(self):
        msg = self.msg_field.text.strip()
        if not msg or not self.teammate:
            return
        self.app.send_message(f"MSG~{self.teammate}~{msg}")
        self.log.add(f"You:  {msg}", ICE_ACCENT)
        self.msg_field.text = ""

    def add_log(self, text, ok=False):
        self.log.add(text, ICE_OK if ok else ICE_DARK)

    # ── draw ──────────────────────────────────────────────────────────────────
    def draw(self, surf):
        SPEED = 4  # פיקסלים לפריים

        # ── smooth movement player 1 ──
        if self.player1 and self.player1_pixel:
            target_x = self.player1[0] * _TILE_SIZE
            target_y = self.player1[1] * _TILE_SIZE
            px, py = self.player1_pixel[0], self.player1_pixel[1]
            if px < target_x:
                px = min(px + SPEED, target_x)
            elif px > target_x:
                px = max(px - SPEED, target_x)
            if py < target_y:
                py = min(py + SPEED, target_y)
            elif py > target_y:
                py = max(py - SPEED, target_y)
            self.player1_pixel = [px, py]

        # ── smooth movement player 2 ──
        if self.player2 and self.player2_pixel:
            target_x = self.player2[0] * _TILE_SIZE
            target_y = self.player2[1] * _TILE_SIZE
            px, py = self.player2_pixel[0], self.player2_pixel[1]
            if px < target_x:
                px = min(px + SPEED, target_x)
            elif px > target_x:
                px = max(px - SPEED, target_x)
            if py < target_y:
                py = min(py + SPEED, target_y)
            elif py > target_y:
                py = max(py - SPEED, target_y)
            self.player2_pixel = [px, py]

        draw_bg(surf)
        self._draw_map(surf)
        self._draw_chat_strip(surf)
        self.log.draw(surf)
        self.msg_field.draw(surf)
        self.btn_send.draw(surf)
        self.btn_disc.draw(surf)

# ══════════════════════════════════════════════════════════════════════════════
#  ClientGUI  (main app controller — drop-in replacement for old ClientGUI)
# ══════════════════════════════════════════════════════════════════════════════

class ClientGUI:
    def __init__(self):
        self.sock            = None
        self.connected       = False
        self.loggedin        = False
        self.send_recv_AES   = None
        self.rsa_mode        = None
        self.mode_stage      = ""
        self.listener_thread = None
        self.user_list       = set()
        self._pending_username = ""
        self._pending_password = ""

        # screens
        self._screens = {}
        self._current  = None
        self.set_screen("connect")



    # ── Screen management ──────────────────────────────────────────────────────
    def set_screen(self, name, **kwargs):
        if name == "connect":  s = ConnectScreen(self)
        elif name == "login":  s = LoginScreen(self)
        elif name == "signup": s = SignupScreen(self)
        elif name == "verify": s = VerifyScreen(self, **kwargs)
        elif name == "newpw":  s = NewPasswordScreen(self, **kwargs)
        elif name == "main":   s = MainScreen(self)
        else: return
        self._current_name = name
        self._current = s

    # ── Networking ─────────────────────────────────────────────────────────────
    def send_message(self, message: str):
        try:
            self.send_recv_AES.send_encrypted(message.encode())
        except Exception as e:
            self._notify(f"Send error: {e}", ok=False)

    def start_listener(self):
        self.listener_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="ServerListener"
        )
        self.listener_thread.start()

    def disconnect(self):
        if not self.connected: return
        self.connected = False
        self.loggedin  = False
        try:
            self.send_message("DSC")
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except Exception:
            pass
        self.sock = None
        self.set_screen("connect")

    def _listen_loop(self):
        while self.connected:
            try:
                if self.mode_stage == "RSA" and self.rsa_mode:
                    self.rsa_mode.recv_public_key()
                    self.send_recv_AES.create()
                    self.rsa_mode.encrypt(self.send_recv_AES.key)
                    self.mode_stage = "AES"

                elif self.mode_stage == "AES":
                    data = self.send_recv_AES.recv_encrypted()
                    if not data:
                        self._notify("[!] Server closed connection.")
                        self.connected = False
                        break
                    self._handle_server_msg(data)

            except Exception:
                if self.connected:
                    traceback.print_exc()
                self.connected = False
                break

    def _handle_server_msg(self, data: bytes):
        if not self.loggedin:
            fields = data.decode().split('~')
            code = fields[0]

            if code == '1SP':
                self.set_screen("verify", next_action="signup")
                return

            if code == 'SIS':
                self._notify("✔ Sign-up complete! You can now log in.", ok=True)
                self.set_screen("login")
                return

            if code == 'POK':
                uname = getattr(self, '_forgot_username', '')
                self.set_screen("newpw", username=uname)
                return

            if code == 'SIL':
                self.loggedin = True
                self._my_username = getattr(self, '_pending_username', '')
                self._notify("✔ Login successful!", ok=True)
                self.set_screen("main")
                self._current.my_player_num = int(fields[1])
                return

        if data[:3] == b'ERR':
            fields = data.decode().split('~')
            self._notify(f"✘ {fields[2]}", ok=False)
            return

        if data[:3] == b'ACC':
            username = data.decode().split('~')[1]
            self._update_users(username, add=True)
            return

        if data[:3] == b'UPD':
            if self._current_name == 'main':
                self._current.set_upd_argvs(data[4:])

        if data[:3] == b'HIT':
            if self._current_name == 'main':
                num = int(data.split(b'~')[1].decode())
                self._current.player_die(num)

        if data[:3] == b'GEN':
            if data[:3] == b'GEN':
                condition = data.split(b'~')[1].decode()

                # Switch the active screen display directly to our new EndScreen layout
                self._current = EndScreen(condition)

                # Start the 4-second timer to close the application (USEREVENT + 11)
                pygame.time.set_timer(pygame.USEREVENT + 11, 4000)
                return

        if data[:3] == b'ACD':
            username = data.decode().split('~')[1]
            self._update_users(username, add=False)
            return

        if data[:3] == b'GMS':
            rest = data[4:]
            i = rest.index(b'~')
            src = rest[:i].decode()
            msg = rest[i+1:].decode()
            self._notify(f"{src}:  {msg}")
            return

    def _notify(self, text, ok=False):
        """Thread-safe: push a message to the current screen if it has a log, else set_msg."""
        scr = self._current
        if isinstance(scr, MainScreen):
            scr.add_log(text, ok=ok)
        elif hasattr(scr, 'set_msg'):
            scr.set_msg(text, ok=ok)

    def _update_users(self, username, add):
        """Track the other player (teammate). Ignore self."""
        my_username = getattr(self, '_my_username', '')
        if username == my_username:
            return
        if add:
            self.user_list.add(username)
        else:
            self.user_list.discard(username)
        # the teammate is whoever is in the set (2-player game)
        teammate = next(iter(self.user_list), "")
        if isinstance(self._current, MainScreen):
            self._current.teammate = teammate

    # ── Main loop ──────────────────────────────────────────────────────────────
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                # new-password: timed redirect back to log in
                if event.type == pygame.USEREVENT + 10:
                    pygame.time.set_timer(pygame.USEREVENT + 10, 0)
                    self.set_screen("login")
                if event.type == pygame.USEREVENT + 11:
                    pygame.time.set_timer(pygame.USEREVENT + 11, 0)
                    running = False
                if self._current:
                    self._current.handle_event(event)

            if self._current:
                self._current.update()

            draw_bg(SCREEN)
            draw_title(SCREEN)
            if self._current:
                self._current.draw(SCREEN)

            pygame.display.flip()
            CLOCK.tick(60)

        self.disconnect()
        pygame.quit()

