风格模板目录（以 .py 源文件分发，可自由添加/删除）

规则：
1. 在本目录放置 *.py（不要以 _ 开头）
2. 文件中定义一个继承 app.themes.base.Theme 的类
3. 必须设置：id / name / width / height
4. 实现 render(self, snap, now, t) -> PIL.Image
   （角度适配主题另见 _theme_orient_template.py：覆盖 canvas_size / render_frame）
5. 重启应用或点击「刷新模板」后生效

角度适配脚手架（以下划线开头，不会出现在主题列表）：
  _theme_orient_template.py   可复制的竖/横双布局代码模板
  _prompt_new_theme.txt       生成新主题时用的提示词

分辨率由模板自己定义；用户选择模板后界面会显示该分辨率。

摆放方向（应用设置）：
  0°/180°  pic = screenW×screenH，再旋转后发送
  90°/270° pic = screenH×screenW，再旋转后发送
  横屏主题可设 preferred_orientation = 90（选中时自动勾选）
  主题可覆盖 render_frame / canvas_size 做按角度切换的双布局

内置主题（灵感参考 https://www.stylekit.top/zh/styles ）：
  landscape_hud_90.py           横屏 HUD（配合 90°）
  flip_clock_portrait.py        翻页时钟（上半时钟 / 下半 AIDA）
  photo_slideshow_portrait.py   照片轮播（纯图全屏）
  aida64_dense_portrait.py      AIDA64 Dense 竖屏
  classic_portrait.py           Classic 竖屏
  cyan_hud_portrait.py          Cyan HUD 竖屏
  mecha_portrait.py             机甲风 Mecha
  neo_brutalist_portrait.py     新野兽派
  bento_grid_portrait.py        便当盒布局
  glass_dark_portrait.py        玻璃暗色
  soft_ui_portrait.py           柔和界面
  editorial_portrait.py         编辑杂志风
  modern_gradient_portrait.py   现代渐变风
  corporate_clean_portrait.py   企业简洁风
  minimal_flat_portrait.py      极简扁平风
  retro_vintage_portrait.py     复古怀旧风
  geometric_bold_portrait.py    几何大胆风
  claymorphism_portrait.py      粘土拟态
  notion_style_portrait.py      Notion 风格
  natural_organic_portrait.py   自然有机风
