alignfacehttp
===

Performs affine transformation of the input image with rescaling. As output you will get face with fixed **distance** between eyes, eyes-line will be horizontal and image dimensions will be scaled to **width**x**height**. Note, that transformation wil be performed only if input image contains single face.

## How to use

Single call to apply alignment: 

```
curl -X POST -F file=@mypic.jpg -F distance=90 -F width=300 -F height=400 http://localhost:5000/align 
```

<img src="/pictures/feynman.jpg" height="350"><img src="/pictures/right_arrow.png" height="350"><img src="/pictures/aligned.jpeg" height="350">

## Installation

```
git clone http://github.com/pi-null-mezon/alignfacehttp.git
cd alignfacehttp
sudo docker build -t alignfacehttp --force-rm .
sudo docker run -p 5000:5000 -d --name alignfacehttp --rm -v ${PWD}:/usr/src/app alignfacehttp
```

## Thanks

* [Opencv](https://opencv.org/)
* [Dlib](http://dlib.net/)






