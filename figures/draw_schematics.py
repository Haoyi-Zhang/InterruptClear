"""Render the cleanup-order and interruptible-phase constructions directly in Python."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

plt.rcParams.update({"font.family":"STIXGeneral", "mathtext.fontset":"stix",
                     "font.size":9, "pdf.fonttype":42, "ps.fonttype":42})


def arrow(ax, start, end, **kwargs):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8,
                                lw=.8, color="black", **kwargs))


def box(ax, x, y, label, width=1.05, height=.48, size=9):
    ax.add_patch(Rectangle((x-width/2, y-height/2), width, height,
                           facecolor="white", edgecolor="black", lw=.8))
    ax.text(x, y, label, ha="center", va="center", fontsize=size)


def save(fig, path):
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    bounds=fig.bbox
    for ax in fig.axes:
        for text in ax.texts:
            b=text.get_window_extent(renderer)
            if b.x0<bounds.x0 or b.y0<bounds.y0 or b.x1>bounds.x1 or b.y1>bounds.y1:
                raise ValueError("Label outside canvas: "+text.get_text())
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path, metadata={"Creator":"Matplotlib", "CreationDate":None,
                                "ModDate":None},facecolor="white")
    plt.close(fig)


def order(path):
    fig=plt.figure(figsize=(3.45,1.6))
    ax=fig.add_axes((.02,.02,.96,.96))
    ax.set(xlim=(-1.05,8.0),ylim=(-1.2,1.65))
    ax.axis("off")
    for y, labels in ((1.0,(r"$P$",r"$C$","use")),(-.05,(r"$C$","commit",r"$P$"))):
        for x,label in zip((.55,3.0,5.45),labels):
            box(ax,x,y,label,width=1.25,height=.5,size=8.5)
        arrow(ax,(1.175,y),(2.375,y))
        arrow(ax,(3.625,y),(4.825,y))
    ax.text(-.3,1.,"safe",ha="right",va="center",fontsize=8)
    ax.text(-.3,-.05,"unsafe",ha="right",va="center",fontsize=8)
    for x,y,label in ((1.77,1.37,r"$p=0$"),(4.22,1.37,r"$t=0$"),
                      (1.77,.34,"interrupt"),(4.22,.34,"return")):
        ax.text(x,y,label,ha="center",va="center",fontsize=7.4)
    ax.text(6.24,-.05,r"$t=1$ at use",ha="left",va="center",fontsize=7.7)
    ax.text(3.45,-.65,r"$P$: cancel pending; $C$: clear taint",ha="center",va="center",fontsize=7.8)
    ax.text(3.45,-1.02,r"Initially $t=p=1$; handler only commits",ha="center",va="center",fontsize=7.8)
    save(fig,path)


def phases(path):
    fig=plt.figure(figsize=(7.1,2.05))
    ax=fig.add_axes((.02,.02,.96,.96))
    ax.set(xlim=(0,9.4),ylim=(-.22,2.65))
    ax.axis("off")
    for x,label in ((.9,r"$q^0$"),(3.35,r"$q^1$"),(5.8,r"$q^2$"),(8.25,r"$v^0$")):
        box(ax,x,1.75,label,width=1.05,height=.48,size=10)
    for left,right,title,cost in ((1.425,2.825,"selected $P$\nclear $p$","base cost 0"),
                                  (3.875,5.275,"selected $C$\nclear $t$","base cost 0"),
                                  (6.325,7.725,"original use","base cost 1")):
        arrow(ax,(left,1.75),(right,1.75))
        ax.text((left+right)/2,2.22,title,ha="center",va="center",fontsize=9)
        ax.text((left+right)/2,1.34,cost,ha="center",va="center",fontsize=8.5)
    for x in (.9,3.35,5.8):
        box(ax,x,.35,"handler entry",width=1.25,height=.48,size=8.7)
        arrow(ax,(x-.24,1.51),(x-.24,.59))
        arrow(ax,(x+.24,.59),(x+.24,1.51))
        ax.text(x-.37,1.02,"interrupt",ha="right",va="center",fontsize=8)
        ax.text(x+.37,1.02,"return",ha="left",va="center",fontsize=8)
    ax.text(8.1,.4,"Same guard and reset\nSame invariant per phase\nResume saved phase",
            ha="center",va="center",fontsize=8.7,linespacing=1.4)
    save(fig,path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir",type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args()
    order(args.outdir/"order.pdf")
    phases(args.outdir/"phases.pdf")
    print("Wrote two embedded-font vector diagrams; labels within canvas.")


if __name__=="__main__":
    main()
