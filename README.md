# noti-reader

This projects aims to bring text to speech for KDE Plasma 5 notifications and filter them using simple and advanced rules.
It consists of the main non-GUI python module and GUI python module, that lets to filter reading rules.
It is a beginner attempt, so please do not judge it hard.
Originally it is using Coqui TTS with VITS model for english, and Silero TTS for russian.
There is a simple logic to detect which language of these two is in notification, and read text in corresponding language.

There is no settings for TTS engines yet, but it will the next thing in development after advanced filters feature. 

Right now the advanced filters in GUI are in the middle of developing, so it doesn't fully work yet.

required software:

https://github.com/coqui-ai/TTS

https://github.com/snakers4/silero-models
