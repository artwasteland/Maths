# Drawings of the 398 minimal forbidden graphs (2026-09-25)

`gallery-398.json` is `tools/gallery_embed.py`'s output: for each of the 74 Globus-Parshall graphs and the 324 of
GP-10, the edge e left dashed and a unit-distance embedding of G - e chosen for legibility, refined at 50 digits.
All 398 are genuine: the worst solid-edge residue is 3.6e-49, the closest two points are 0.124 apart (median 0.50),
the closest a point comes to an edge it is not on is 0.124 (median 0.26), and the dashed lengths run from 0.19 to 4.52
(none within 0.10 of 1). `cert-types.json` gives each graph's refutation type (from the certified runs), and
`../../gallery/the-398.html` is the page `tools/write_gallery.py` builds from both (it refuses on any non-genuine
drawing). 5,689 s on two cores.
