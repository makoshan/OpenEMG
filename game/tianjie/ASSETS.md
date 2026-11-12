# 资源与许可

- Three.js 0.186.0：MIT；许可随 dist/assets/three-LICENSE.txt 保存。
- 手部 GLB：immersive-web/webxr-input-profiles generic-hand/right.glb，MIT（Amazon 2019），许可 dist/assets/hand-LICENSE.txt。来源 https://cdn.jsdelivr.net/npm/@webxr-input-profiles/assets@1.0.16/dist/profiles/generic-hand/right.glb 。本原型另加衣袖、手环和输入驱动姿态。
- 石庭 PBR：Poly Haven `cobblestone_floor_001`，1K diffuse/normal/roughness，CC0。https://polyhaven.com/a/cobblestone_floor_001
- 山石 PBR：Poly Haven `rock_boulder_dry`，1K diffuse/normal/roughness，CC0。https://polyhaven.com/a/rock_boulder_dry
- 远景：OpenAI ImageGen 生成，保存为 dist/assets/sky-mountains.png。创作描述：2:1 panoramic cinematic Chinese sacred limestone mountains floating above a sea of clouds at blue hour, warm golden sunlight from upper right, distant tiny temples, photoreal natural stone and atmospheric perspective, lower quarter mist, no foreground, no characters, no UI or text. 仅作远景，建筑、敌人、手部与战斗实时渲染。
- 建筑、敌人、法阵纹理、光效与合成音效：本项目代码生成。
- 字体：浏览器可加载 Google Fonts Noto Serif SC；App 沙箱阻止外网字体，回退系统中文衬线字体。
- 《掌天诀》标题 Logo：OpenAI ImageGen 生成，透明底 PNG，保存于 app/game/tianjie/assets/zhangtian-logo.png，游戏首页与页首复用。创作方向：玄金书法“掌天诀”，五指／天柱托起诸天，掌心纵向裂隙，少量朱砂篆印，无额外标语。生成日期 2026-10-15。本次未使用外部游戏 Logo。
- 手部调整：在既有 MIT 骨骼网格上做 Loop 细分，混合并归一化骨骼权重；指甲、关节细纹与肤色变化为同一 skinned surface 上的程序着色，不增加脱离手指的甲片。

## 2026-10-16 参考设计美术

- `app/game/tianjie/assets/sky-night.jpg`：内置 OpenAI image_gen，参考用户提供的《游戏封面.png》配色生成独立夜空；JPEG 85% 作游戏纹理。仅用于第一关，首关清敌过门时渐退，之后仍用原山景及原亭子锚点。
- `app/game/tianjie/assets/seal-{sword,guard,thunder}.png`：内置 image_gen 以用户提供的三张技能设计图生成的透明手势图标；缩至最大边 384px，保留 alpha。仅作界面插画；实际第一人称手仍为 MIT 骨骼网格实时驱动。肌电示范口令与硬件识别协议保持 PR #103 口径，插画不是识别验证证据。
- `app/game/tianjie/assets/game-icon.png`：用户提供的 `logo.png`，缩至 192px 用作 favicon。页面中文字标继续用既有透明金色标题，避免把整张方形封面塞入 HUD。
- 完整最终提示词见 `art-prompts-20261016.json`。原始设计文件不入库，未上传肌电或佩戴数据。
- 本轮实时美术：夜/月光与暖灯、日出过渡、湿石地面、黑色褶皱袖口、薄黑环青灯、皮肤微法线、蓝色飞剑尾流、金符护身与金橙雷电、妖影下坠崩解。没有把概念图平铺成游戏；程序网格仍有原型精度限制。
- 新增运行时图像合计约 791 KiB；从干净目录执行 `npm run assets -- ../../app/game/tianjie/assets` 会复制全部新旧素材，缺少必需美术会明确失败。

## Ascension ending (2026-10-16)

- `ending-cloudsea.jpg`: generated using the built-in `image_gen` tool for the final cloud-sea background; original 1672×941 PNG converted to JPEG quality 86 for runtime. Full prompt and generation mode: `ending-art-prompt-20261016.json`. No reference photograph or private data uploaded for this asset.
- The victory scene uses procedural golden light currents, feathers, clouds and a celestial halo, then fades into the existing transparent Zhangtian logo. No hand-shaped mountain is used. The background is a 2D matte painting; the effects and camera are rendered live.

## 一掌开天终章（2026-10-17）

- `ending-heaven.jpg`：内置 image_gen 生成仙宫、悬山、瀑布与日轮的新天地远景，1672×941，JPEG quality 88。完整提示词见 `ending-art-prompt-20261017.json`。
- 该图是环境底图。裂隙生长与分离、手臂推掌、冲击光流、近景云层、羽流、镜头推进与仙宫回应由游戏实时驱动；不要求玩家再做一次手势。
- 新增的骤静/心跳/裂天/开天/腾空/仙宫回应/Logo乐句由本地 Web Audio 合成；没有新增外部录音或采集用户音频。
