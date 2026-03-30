import numpy as np
import matplotlib.pyplot as pl

sr = 3
# sr -3 .. +3
u = (np.random.random(1000) * 2 - 1) * sr
v = (np.random.random(1000) * 2 - 1) * sr

# simple gaussian correl in y
y = np.exp(-(u*u+v*v)/5)

# add some noise
y += 0.005 * np.random.randn(1000)

# transform to 2nd order poly
y = np.log(y)

# apply normal equation
X_b = np.c_[np.ones(u.shape[0]), u, v, u * v, u * u, v * v]
theta_hat = np.linalg.inv(X_b.T.dot(X_b)).dot(X_b.T).dot(y)

# predict y for a range of u and v
ur, vr = np.linspace(-sr, sr), np.linspace(-sr, sr)
ui, vi = np.meshgrid(ur, vr)

X = np.c_[
    ui.ravel(), vi.ravel(), ui.ravel() * vi.ravel(), ui.ravel() ** 2, vi.ravel() ** 2
]
X_b = np.c_[np.ones(X.shape[0]), X]
y_predict = X_b.dot(theta_hat)
y_predict.shape = ui.shape

# visualize in log space
fg, ax = pl.subplots(subplot_kw={"projection": "3d"})
ax.scatter(u, v, y, s=2, c=y)
ax.plot_surface(ui, vi, y_predict, alpha=0.1)
ax.set_xlabel("u")
ax.set_ylabel("v")
ax.set_zlabel("y")
pl.tight_layout()
pl.show()

# visualize in original space
fg, ax = pl.subplots(subplot_kw={"projection": "3d"})
y = np.exp(y)
y_predict = np.exp(y_predict)
ax.scatter(u, v, y, s=2, c=y)
ax.plot_surface(ui, vi, y_predict, alpha=0.1)
ax.set_xlabel("u")
ax.set_ylabel("v")
ax.set_zlabel("y")
pl.tight_layout()
pl.show()
