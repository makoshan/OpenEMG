/* App 进程里发鼠标事件。辅助功能权限挂在这个 App 上，不能交给没有 Quartz 的采集 Python。
 * 只编译 darwin-arm64，给 Electron 44 的 NODE_MODULE_VERSION。检查不发事件，只读光标位置：
 *   clang -bundle -undefined dynamic_lookup -arch arm64 \
 *     -I "$HDR/include/node" -DNODE_GYP_MODULE_NAME=emg8_mouse \
 *     -o emg8-mouse.node emg8-mouse.c -framework CoreGraphics
 */
#include <math.h>
#include <node_api.h>
#include <stdbool.h>
#include <string.h>
#include <unistd.h>
#include <CoreGraphics/CoreGraphics.h>

static double clamp_step(double v) {
  if (!isfinite(v)) return 0;
  if (v > 400) return 400;
  if (v < -400) return -400;
  return v;
}

/* 滚动按行算，夹在 ±10 行；正 = 内容向上（往下翻），和采集服务 wl8_cursor.py 的约定一致 */
static int clamp_lines(double v) {
  if (!isfinite(v)) return 0;
  if (v > 10) return 10;
  if (v < -10) return -10;
  return (int)lround(v);
}

static bool current_pos(CGPoint *out) {
  CGEventRef ev = CGEventCreate(NULL);
  if (!ev) return false;
  *out = CGEventGetLocation(ev);
  CFRelease(ev);
  return true;
}

static void post_event(CGEventType type, CGPoint p, CGMouseButton button) {
  CGEventRef ev = CGEventCreateMouseEvent(NULL, type, p, button);
  if (!ev) return;
  CGEventPost(kCGHIDEventTap, ev);
  CFRelease(ev);
}

static napi_value Where(napi_env env, napi_callback_info info) {
  (void)info;
  CGPoint p;
  napi_value obj, x, y;
  if (!current_pos(&p)) {
    napi_throw_error(env, "no-cursor", "读不到光标位置");
    return NULL;
  }
  napi_create_object(env, &obj);
  napi_create_double(env, p.x, &x);
  napi_create_double(env, p.y, &y);
  napi_set_named_property(env, obj, "x", x);
  napi_set_named_property(env, obj, "y", y);
  return obj;
}

static napi_value Post(napi_env env, napi_callback_info info) {
  size_t argc = 3;
  napi_value args[3];
  char action[32];
  size_t n = 0;
  double dx = 0, dy = 0;
  CGPoint p;
  napi_get_cb_info(env, info, &argc, args, NULL, NULL);
  if (argc < 3) {
    napi_throw_error(env, "bad-action", "未知动作");
    return NULL;
  }
  napi_get_value_string_utf8(env, args[0], action, sizeof action, &n);
  napi_get_value_double(env, args[1], &dx);
  napi_get_value_double(env, args[2], &dy);
  if (strcmp(action, "scroll") == 0) {
    int lines = clamp_lines(dy);
    CGEventRef ev = CGEventCreateScrollWheelEvent(NULL, kCGScrollEventUnitLine, 1, -lines);
    if (ev) {
      CGEventPost(kCGHIDEventTap, ev);
      CFRelease(ev);
    }
    napi_value undef_scroll;
    napi_get_undefined(env, &undef_scroll);
    return undef_scroll;
  }
  dx = clamp_step(dx);
  dy = clamp_step(dy);
  if (!current_pos(&p)) {
    napi_throw_error(env, "no-cursor", "读不到光标位置");
    return NULL;
  }
  if (strcmp(action, "move") == 0) {
    CGRect b = CGDisplayBounds(CGMainDisplayID());
    p.x += dx;
    p.y += dy;
    if (p.x < 0) p.x = 0;
    if (p.y < 0) p.y = 0;
    if (p.x > b.size.width - 1) p.x = b.size.width - 1;
    if (p.y > b.size.height - 1) p.y = b.size.height - 1;
    post_event(kCGEventMouseMoved, p, kCGMouseButtonLeft);
  } else if (strcmp(action, "left_click") == 0) {
    post_event(kCGEventLeftMouseDown, p, kCGMouseButtonLeft);
    usleep(30000);
    post_event(kCGEventLeftMouseUp, p, kCGMouseButtonLeft);
  } else if (strcmp(action, "right_click") == 0) {
    post_event(kCGEventRightMouseDown, p, kCGMouseButtonRight);
    usleep(30000);
    post_event(kCGEventRightMouseUp, p, kCGMouseButtonRight);
  } else {
    napi_throw_error(env, "bad-action", "未知动作");
    return NULL;
  }
  napi_value undef;
  napi_get_undefined(env, &undef);
  return undef;
}

static napi_value Init(napi_env env, napi_value exports) {
  napi_value post, where;
  napi_create_function(env, "post", NAPI_AUTO_LENGTH, Post, NULL, &post);
  napi_create_function(env, "where", NAPI_AUTO_LENGTH, Where, NULL, &where);
  napi_set_named_property(env, exports, "post", post);
  napi_set_named_property(env, exports, "where", where);
  return exports;
}

NAPI_MODULE(NODE_GYP_MODULE_NAME, Init)
