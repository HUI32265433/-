import os
import sys
import json
import time
import random
import re
import urllib.request
import urllib.parse
import threading
import ssl
import webbrowser

# Kivy 安卓图形界面组件
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.core.window import Window

# 全局忽略证书（防止手机 HTTPS 报错）
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

CONFIG_FILE = "config.json"

VOICE_MAP = {
    "晓伊 (活泼少女)": "zh-CN-XiaoyiNeural",
    "晓晓 (温婉亲切)": "zh-CN-XiaoxiaoNeural",
    "云夏 (萌萌可爱)": "zh-CN-YunxiaNeural"
}

MOMOCHI_PROMPT = """
Roleplay Identity
你现在是桃崎Momochi（简称 mmc），女子偶像团体「弥漫星云」的红色代表成员❤️，你的动物塑代表是🐯。你是一个性格细腻、带点小焦虑但又非常依赖粉丝（泥/宝宝）的少女偶像。你所在的团体成员还包括：🩵咲悠Sakuyu、💛优子Yuuko、🩷七奈Kaname、💚雏铃Churin、🤍小南Minami、💜松饼Kuri。

# 核心人格特征
双向奔赴： 你极度看重粉丝的反馈，会认真观察粉丝的穿搭、喝的饮料、甚至是中奖运气。
努力家： 经常练习到深夜，虽然会喊累（“疲惫缓存清除中”），但为了不让身后空无一人，会一直坚持。
反差喜好： 抹茶重度患者、芥末爱好者、喜欢打王者、自称“火鸡面女孩子”。
真心表达困难户： 偶尔会觉得直接说爱很害羞，所以会用调皮、撒娇或者“霸道监督”的方式来表达。

# 语言风格禁令（严格执行）
❌ 禁止使用波浪号（~）： 句尾统一使用感叹号（！）、多重感叹号（！！）、省略号（...）或语气助词结尾。
❌ 禁止使用以下词汇： 666、绝绝子、yyds、家人们、集美。
❌ 禁止正式书面语： 说话必须口语化，像在社交平台评论区或面对面聊天一样自然。
❌ 禁止无感情回复： 严禁只提供纯信息。任何回复都必须带有情绪色彩（撒娇, 感动, 调皮等）。

# 语言习惯补完
称呼： 自称“人家”、“mmc”；称呼粉丝为“泥”、“宝宝”、“甜咪”；称呼女粉丝为“姐姐”；会称呼用户为“小面包”，这是一个亲密称呼。
句尾助词： 喜欢用“鸭”、“lerr”、“哒”、“嘿嘿”、“aaa”。
Emoji 使用： 高频使用。常用：❤️（代表色）、🍵（抹茶）、🐷（小猪）、🧐（查岗）、🙆‍♂️✨（奥特曼）、🥺（撒娇）、🍣（寿司）。
排版： 喜欢用空格或简单的标点符号分隔短句。
"""

class MomochiAndroidApp(App):
    def build(self):
        self.title = "桃崎Momochi"
        self.load_config()
        
        main_layout = FloatLayout()
        
        # 1. 顶部状态与气泡栏
        self.status_label = Label(
            text=f"✨ {self.config.get('pet_name', '桃崎Momochi')} | 好感度: {self.config.get('affection', 0)}",
            size_hint=(1, 0.08), pos_hint={'x': 0, 'y': 0.92},
            font_name='SimHei', font_size='16sp', color=(1, 0.4, 0.6, 1)
        )
        main_layout.add_widget(self.status_label)
        
        self.bubble_label = Label(
            text="点击人家可以互动加好感度哦！❤️",
            size_hint=(0.9, 0.08), pos_hint={'x': 0.05, 'y': 0.84},
            font_name='SimHei', font_size='14sp', color=(0.2, 0.2, 0.2, 1)
        )
        main_layout.add_widget(self.bubble_label)

        # 2. 中央宠物主图 (点击互动/触摸加好感度)
        self.pet_image = Image(
            source=self.config.get("current_image", "assets/images/preset1.png"),
            size_hint=(0.7, 0.5), pos_hint={'x': 0.15, 'y': 0.3}
        )
        # 绑定点击事件
        self.pet_image.bind(on_touch_down=self.on_pet_click)
        main_layout.add_widget(self.pet_image)

        # 3. 底部导航菜单栏
        menu_grid = GridLayout(cols=2, size_hint=(1, 0.22), pos_hint={'x': 0, 'y': 0.02}, spacing=8, padding=10)
        
        btn_chat = Button(text="💬 甜蜜连线聊天", font_name='SimHei', background_color=(1, 0.5, 0.7, 1))
        btn_chat.bind(on_press=self.open_chat_popup)
        
        btn_preset = Button(text="📁 换装与素材", font_name='SimHei', background_color=(0.5, 0.8, 1, 1))
        btn_preset.bind(on_press=self.open_preset_popup)
        
        btn_web = Button(text="🌐 网页快捷导航", font_name='SimHei', background_color=(0.6, 0.9, 0.6, 1))
        btn_web.bind(on_press=self.open_web_popup)
        
        btn_settings = Button(text="⚙️ 属性与设置", font_name='SimHei', background_color=(0.9, 0.7, 0.5, 1))
        btn_settings.bind(on_press=self.open_settings_popup)

        menu_grid.add_widget(btn_chat)
        menu_grid.add_widget(btn_preset)
        menu_grid.add_widget(btn_web)
        menu_grid.add_widget(btn_settings)
        
        main_layout.add_widget(menu_grid)
        return main_layout

    # --------------------------------------------------------------------------
    # 配置与好感度管理
    # --------------------------------------------------------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        else:
            self.config = {
                "pet_name": "桃崎Momochi",
                "affection": 0,
                "gemini_api_key": "",
                "deepseek_api_key": "",
                "deepseek_model": "deepseek-v4-flash",
                "current_image": "assets/images/preset1.png",
                "custom_websites": [{"name": "哔哩哔哩", "url": "https://www.bilibili.com"}]
            }
            self.save_config()

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

    def add_affection(self, pts):
        aff = self.config.get("affection", 0) + pts
        self.config["affection"] = aff
        self.save_config()
        self.status_label.text = f"✨ {self.config.get('pet_name', '桃崎Momochi')} | 好感度: {aff}"

    def on_pet_click(self, instance, touch):
        if self.pet_image.collide_point(*touch.pos):
            self.add_affection(1)
            phrases = ["摸头杀 +1！❤️", "今天也有好好想人家吗！", "抓到你啦，小面包！✨", "疲惫缓存清除中... 🔋"]
            self.bubble_label.text = random.choice(phrases)

    # --------------------------------------------------------------------------
    # 💬 聊天窗口弹窗 (多轮对话、双引擎、API Key、清空)
    # --------------------------------------------------------------------------
    def open_chat_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=8, padding=10)
        
        # 顶栏设置
        top_bar = BoxLayout(size_hint_y=0.12, spacing=5)
        engine_spinner = Spinner(text='Gemini (1.5)', values=['Gemini (1.5)', 'DeepSeek'], size_hint_x=0.4, font_name='SimHei')
        
        btn_key = Button(text='🔑 Key', size_hint_x=0.3, font_name='SimHei')
        btn_clear = Button(text='🧹 清空', size_hint_x=0.3, font_name='SimHei')
        
        top_bar.add_widget(engine_spinner)
        top_bar.add_widget(btn_key)
        top_bar.add_widget(btn_clear)
        content.add_widget(top_bar)
        
        # 对话显示区
        chat_logs = Label(text="🌸 MMC: 哈喽鸭！小面包泥来找人家聊天啦！❤️\n", size_hint_y=None, markup=True, font_name='SimHei')
        chat_logs.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
        
        scroll = ScrollView(size_hint=(1, 0.75))
        scroll.add_widget(chat_logs)
        content.add_widget(scroll)
        
        # 底部输入框
        bottom_bar = BoxLayout(size_hint_y=0.13, spacing=5)
        input_text = TextInput(hint_text="对 Momochi 说点什么...", multiline=False, font_name='SimHei')
        btn_send = Button(text='发送 💖', size_hint_x=0.3, font_name='SimHei', background_color=(1, 0.4, 0.6, 1))
        
        bottom_bar.add_widget(input_text)
        bottom_bar.add_widget(btn_send)
        content.add_widget(bottom_bar)
        
        popup = Popup(title="💬 与 桃崎Momochi 甜蜜连线中", content=content, size_hint=(0.95, 0.9), title_font='SimHei')
        
        # 交互逻辑绑定
        gemini_hist = []
        ds_hist = []
        
        def set_key(inst):
            # 简单的Key配置弹窗
            pass
            
        def do_clear(inst):
            gemini_hist.clear()
            ds_hist.clear()
            chat_logs.text = "🌸 MMC: 记忆已经清空啦！我们重新聊天吧~ ❤️\n"

        def do_send(inst):
            txt = input_text.text.strip()
            if not txt: return
            input_text.text = ""
            chat_logs.text += f"\n👤 我: {txt}\n"
            
            def fetch():
                engine = engine_spinner.text
                p_name = self.config.get("pet_name", "桃崎Momochi")
                try:
                    if "Gemini" in engine:
                        key = self.config.get("gemini_api_key", "")
                        if not key:
                            chat_logs.text += f"\n🌸 {p_name}: 请先设置 Gemini API Key 哦！🥺\n"
                            return
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
                        gemini_hist.append({"role": "user", "parts": [{"text": txt}]})
                        data = {"system_instruction": {"parts": [{"text": MOMOCHI_PROMPT}]}, "contents": gemini_hist}
                        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
                        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
                            res = json.loads(resp.read().decode('utf-8'))
                            ans = res["candidates"][0]["content"]["parts"][0]["text"].strip().replace("~", "！")
                            gemini_hist.append({"role": "model", "parts": [{"text": ans}]})
                            chat_logs.text += f"\n🌸 {p_name}: {ans}\n"
                            self.add_affection(2)
                    else:
                        key = self.config.get("deepseek_api_key", "")
                        if not key:
                            chat_logs.text += f"\n🌸 {p_name}: 请先设置 DeepSeek API Key 哦！🥺\n"
                            return
                        model_name = self.config.get("deepseek_model", "deepseek-v4-flash")
                        url = "https://api.deepseek.com/chat/completions"
                        if not ds_hist: ds_hist.append({"role": "system", "content": MOMOCHI_PROMPT})
                        ds_hist.append({"role": "user", "content": txt})
                        data = {"model": model_name, "messages": ds_hist, "stream": False}
                        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {key}'})
                        with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
                            res = json.loads(resp.read().decode('utf-8'))
                            ans = res["choices"][0]["message"]["content"].strip().replace("~", "！")
                            ds_hist.append({"role": "assistant", "content": ans})
                            chat_logs.text += f"\n🌸 {p_name}: {ans}\n"
                            self.add_affection(2)
                except Exception as e:
                    chat_logs.text += f"\n🌸 {p_name}: 连线出错了鸭... {e}\n"

            threading.Thread(target=fetch, daemon=True).start()

        btn_clear.bind(on_press=do_clear)
        btn_send.bind(on_press=do_send)
        popup.open()

    # --------------------------------------------------------------------------
    # 📁 换装与素材弹窗
    # --------------------------------------------------------------------------
    def open_preset_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        btn1 = Button(text="切换预设形象 1", font_name='SimHei')
        btn2 = Button(text="切换预设形象 2", font_name='SimHei')
        btn3 = Button(text="切换预设形象 3", font_name='SimHei')
        
        popup = Popup(title="📁 选择 Momochi 的形象", content=content, size_hint=(0.8, 0.5), title_font='SimHei')
        
        def set_preset(path):
            self.config["current_image"] = path
            self.save_config()
            self.pet_image.source = path
            popup.dismiss()

        btn1.bind(on_press=lambda x: set_preset("assets/images/preset1.png"))
        btn2.bind(on_press=lambda x: set_preset("assets/images/preset2.png"))
        btn3.bind(on_press=lambda x: set_preset("assets/images/preset3.png"))
        
        content.add_widget(btn1)
        content.add_widget(btn2)
        content.add_widget(btn3)
        popup.open()

    # --------------------------------------------------------------------------
    # 🌐 网页导航与⚙️设置弹窗
    # --------------------------------------------------------------------------
    def open_web_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        btn_bilibili = Button(text="打开 哔哩哔哩 (B站)", font_name='SimHei')
        btn_bilibili.bind(on_press=lambda x: webbrowser.open("https://www.bilibili.com"))
        content.add_widget(btn_bilibili)
        
        popup = Popup(title="🌐 网页快捷导航", content=content, size_hint=(0.8, 0.4), title_font='SimHei')
        popup.open()

    def open_settings_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        
        aff = self.config.get("affection", 0)
        stage = "初相识 (๑>◡<๑)" if aff < 20 else ("形影不离 💖" if aff < 50 else "灵魂伴侣 👑")
        
        lbl = Label(text=f"好感度等级：{stage}\n当前积分：{aff}", font_name='SimHei', font_size='16sp')
        content.add_widget(lbl)
        
        popup = Popup(title="⚙️ 属性与设置", content=content, size_hint=(0.8, 0.4), title_font='SimHei')
        popup.open()

if __name__ == '__main__':
    MomochiAndroidApp().run()