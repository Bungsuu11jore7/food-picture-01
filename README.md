# The Golden Melt Burger

A tall, juicy cheeseburger painted pixel by pixel in pure Python: a glossy
golden sesame-seed top bun catching warm light, melted orange cheese
dripping down the sides of a thick seared patty, fresh wavy lettuce and a
glossy red tomato slice, all sitting on a warm wooden board with a small
red carton of golden fries behind it for diner colour and depth. Steam
rises off the hot bun against a warm glowing backdrop, with a dark wooden
table along the bottom of the frame.

## Run

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024x1024, deterministic — two runs produce
byte-identical files). Pure standard library only, no network.
