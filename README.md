关于
====
kwplayer是linux桌面下的网络音乐播放工具, 它使用了kuwo.cn的音乐资源.
注意: 程序尚在开发当中, 可能会出现各种问题, 欢迎提交bug.

安装
====
可以直接运行kuwo.py, 而不需要安装. 但是仍然需要手动安装一些软件包, 它们是:
python3-gi  -  gkt3的python3绑定;
python3-leveldb  -  leveldb的python3绑定;
gstreamer1.0-libav  -  gstreamer的编码/解码库.


对于debian系列的发行版, 也可以直接运行build/下面的脚本, 生成deb包.

Q&A
===
问: 为什么只使用mp3(192K)和ape两种格式的音乐?
答: 其它格式都不太适用, 比如wma的音质不好; 而192K的mp3对于一般用户已经足够好了; 而对于音乐发烧友来说, 320K的mp3格式的质量仍然是很差劲的, 只有ape才能满足他(她)们的要求. 举例来说, 192K的mp3大小是4.7M, 320K的mp3是7.2M, 而对应的ape格式的是31.5M左右, 这就是差距.
总之, 这两种格式足够了.


TODO
====
优化歌词的显示效果
 自动修复mp3的tag编码
支持打开本地的多媒体资源(已放弃)
国际化(i18n)


截图
====
<img src="screenshot.jpg" title="kuwo" />
