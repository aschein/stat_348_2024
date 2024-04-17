import numpy as np
import numpy.random as rn
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageDraw
import itertools as it


def plot_grid(img, cell_size=20):
    # Create a grid
    width, height = img.size

    # Crop image so it is divisible by cell_size
    width = width - (width % cell_size)
    height = height - (height % cell_size)

    img = img.crop((-1, -1, width, height))

    grid = []
    for x in range(0, width, cell_size):
        row = []  # the grid will support (x,y) indexing
        for y in list(range(0, height, cell_size))[::-1]:
            box = (x, y, x+cell_size, y+cell_size)
            row.append(box)
        grid.append(row)

    # Overlay the grid onto the image
    draw = ImageDraw.Draw(img)
    for row in grid:
        for box in row:
            draw.rectangle(box, outline=(255, 255, 255))
    
    return grid, img

def plot_course(seq, grid, img):
    cell_size = grid[0][0][2]-grid[0][0][0]

    point_radius = 2
    point_color = (150, 25, 25)  # green

    final_radius = 4
    final_color = (255, 25, 25)

    arrow_width = 1
    arrow_color = (100, 25, 25)  # red

    draw = ImageDraw.Draw(img)
    for i, (row, col) in enumerate(seq):
        box = grid[row][col]
        x1, y1 = box[0] + (cell_size // 2), box[1] + (cell_size // 2)  # center of cell
        if i == len(seq) - 1:
            draw.ellipse((x1-final_radius, y1-final_radius, x1+final_radius, y1+final_radius), fill=final_color)
        else:
            draw.ellipse((x1-point_radius, y1-point_radius, x1+point_radius, y1+point_radius), fill=point_color)

            row2, col2 = seq[i+1]
            if (row, col) == (row2, col2):
                continue

            box2 = grid[row2][col2]
            x2, y2 = box2[0] + (cell_size // 2), box2[1] + (cell_size // 2)  # center of next cell
            draw.line((x1, y1, x2, y2), width=arrow_width, fill=arrow_color)
            dx, dy = x2 - x1, y2 - y1
            length = (dx ** 2 + dy ** 2) ** 0.5
    return img

def get_scorpion_search_grid(image_path='underwater.png'):
    CELL_SIZE = 20
    ORIGIN_CELL = (16, 12)
    img = Image.open('underwater.png')
    grid, img = plot_grid(img, cell_size=CELL_SIZE)
    return grid, img

def plot_scorpion_search_grid(image_path='underwater.png', show=False):
    grid, img = get_scorpion_search_grid(image_path)
    if show:
        plt.imshow(img)
        plt.xticks(()); plt.yticks(())
        plt.show()
    else:
        return img

def plot_scorpion_path(seq, img=None, grid=None, image_path='underwater.png', show=False):
    if img is None or grid is None:
        grid, img = get_scorpion_search_grid(image_path)
    img = plot_course(seq, grid, img)
    if show:
        plt.imshow(img)
        plt.xticks(()); plt.yticks(())
        plt.show()
    else:
        return img

def plot_dist_on_grid(dist, img, grid, max_alpha=255, vmin=0.1, show=False):
    # Convert data to a NumPy array and normalize
    data_array = np.array(dist).copy()
    assert data_array.shape == np.array(grid).shape[:2]
    normalized_data = data_array / np.max(data_array)
    normalized_data *= (1-vmin)
    normalized_data += vmin
    # Create a new image with the same size as the original
    
    new_img = Image.new('RGBA', img.size, (0, 0, 0, 255))

    # Iterate over each grid cell, adjust the alpha value, and paste it onto the new image
    for i, row in enumerate(grid):
        for j, box in enumerate(row):
            alpha_factor = int(normalized_data[i, j] * max_alpha)
            cell_img = img.crop(box).convert('RGBA')
            alpha_layer = Image.new('L', cell_img.size, alpha_factor)
            cell_img.putalpha(alpha_layer)
            new_img.paste(cell_img, box, cell_img)

    # Draw grid lines on the new image
    draw = ImageDraw.Draw(new_img)
    for row in grid:
        for box in row:
            draw.rectangle(box, outline=(255, 255, 255))
    if show:
        plt.imshow(new_img)
        plt.xticks(()); plt.yticks(())
        plt.show()
    else:
        return new_img

def plot_dist_on_scorpion_search_grid(dist, max_alpha=255, vmin=0.01, show=False, image_path='underwater.png'):
    grid, img = get_scorpion_search_grid(image_path)
    new_img = plot_dist_on_grid(dist=dist, img=img, grid=grid, max_alpha=max_alpha, vmin=vmin)
    if show:
        plt.imshow(new_img)
        plt.xticks(()); plt.yticks(())
        plt.show()
    else:
        return new_img

# increasing x means going east
# decreasing x means going west
# increasing y means going north
# decreasing y means going south

def get_transition_tensor(grid, scenario, avg_depth_vals=None):
    assert scenario in ['flounder', 'evade', 'drift', 'seek_shallow', 'seek_ridge', 'reverse_course']

    n_rows, n_cols = np.array(grid).shape[:2]
    n_cells = n_rows * n_cols

    transition_tensor = np.zeros((n_rows, n_cols, n_rows, n_cols))

    for x1, y1 in np.ndindex((n_rows, n_cols)):
        for (dx, dy) in it.product([-1,0,1], [-1,0,1]):
            if (x1+dx < 0) or (x1+dx >= n_rows) or (y1+dy < 0) or (y1+dy >= n_cols):
                continue
            
            val = 1.0
            
            if scenario == 'evade':
                # the sub never stays place and prefers diagonals
                if (dx == 0) and (dy == 0):
                    val = 0.1
                elif (dx == 0) or (dy == 0):
                    val = 1.
                else:
                    val = 10.
            
            elif scenario == 'flounder':
                # the sub usually stays place
                if (dx == 0) and (dy == 0):
                    val = 10.
                elif (dx == 0) or (dy == 0):
                    val = 1.
                else:
                    val = 0.1
            
            elif scenario == 'drift':
                # the sub drifts with the eastward current (dx=1)
                if (dx == -1):  # drifting west against current
                    val = 0.1
                elif (dx == 1): # drifting east with current
                    if (dy == 0):
                        val = 10.
                    else:
                        val = 3.
                else:
                    val = 1.
            
            elif scenario == 'reverse_course':
                # the sub heads northeast back to spain
                if (dy == 1) and (dx == 1): # heading northeast
                    val = 10
                elif (dy == 1) or (dx == 1): # heading north or east
                    val = 1.
                else:
                    val = 0.1
            
            elif scenario in ['seek_shallow', 'seek_ridge']:
                assert avg_depth_vals is not None
                val = avg_depth_vals[x1+dx, y1+dy]
                if (dx != 0) or (dy != 0):
                    for m in range(2,4):
                        try:
                            val += avg_depth_vals[x1+dx*m, y1+dy*m] # look ahead in same direction
                        except IndexError:
                            pass
                
                if scenario == 'seek_shallow':
                    val = 1. / val
                
                elif scenario == 'seek_ridge':
                    if (x1 < 25) and (dx != 1):
                        val = 0.1
                    
                    if (y1 < 10) and (dy != 1):
                        val = 0.1
            
            transition_tensor[x1, y1, x1+dx, y1+dy] = val

    transition_tensor /= np.sum(transition_tensor, axis=(2,3), keepdims=True)
    assert np.allclose(transition_tensor.sum(axis=(2,3)), 1.)
    return transition_tensor
