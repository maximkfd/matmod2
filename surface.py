import numpy as np


# noinspection PyUnresolvedReferences
class PlaneWaves(object):
    def __init__(self, size=(100, 100), nwave=5, max_height=0.2):
        self._size = size
        self._wave_vector = 5 * (2 * np.random.rand(nwave, 2) - 1)
        self._angular_frequency = 2 * np.random.rand(nwave)
        self._phase = 2 * np.pi * np.random.rand(nwave)
        self._amplitude = max_height * (1 + np.random.rand(nwave)) / 2 / nwave
        self.t = 0

    def position(self):
        xy = np.empty(self._size + (2,), dtype=np.float32)
        xy[:, :, 0] = np.linspace(-1, 1, self._size[0])[:, None]
        xy[:, :, 1] = np.linspace(-1, 1, self._size[1])[None, :]
        return xy

    def propagate(self, dt):
        self.t += dt

    def height_and_normal(self):
        x = np.linspace(-1, 1, self._size[0])[:, None]
        y = np.linspace(-1, 1, self._size[1])[None, :]
        z = np.zeros(self._size, dtype=np.float32)
        grad = np.zeros(self._size + (2,), dtype=np.float32)
        for n in range(self._amplitude.shape[0]):
            arg = self._phase[n] + x * self._wave_vector[n, 0] + y * self._wave_vector[n, 1] + self.t * \
                                                                                               self._angular_frequency[
                                                                                                   n]
            z[:, :] += self._amplitude[n] * np.cos(arg)
            dcos = -self._amplitude[n] * np.sin(arg)
            grad[:, :, 0] += self._wave_vector[n, 0] * dcos
            grad[:, :, 1] += self._wave_vector[n, 1] * dcos
        return z, grad

    def triangulation(self):
        a = np.indices((self._size[0] - 1, self._size[1] - 1))
        b = a + np.array([1, 0])[:, None, None]
        c = a + np.array([1, 1])[:, None, None]
        d = a + np.array([0, 1])[:, None, None]
        a_r = a.reshape((2, -1))
        b_r = b.reshape((2, -1))
        c_r = c.reshape((2, -1))
        d_r = d.reshape((2, -1))
        a_l = np.ravel_multi_index(a_r, self._size)
        b_l = np.ravel_multi_index(b_r, self._size)
        c_l = np.ravel_multi_index(c_r, self._size)
        d_l = np.ravel_multi_index(d_r, self._size)
        abc = np.concatenate((a_l[..., None], b_l[..., None], c_l[..., None]), axis=-1)
        acd = np.concatenate((a_l[..., None], c_l[..., None], d_l[..., None]), axis=-1)
        return np.concatenate((abc, acd), axis=0).astype(np.uint32)


class CircularWaves(PlaneWaves):
    def __init__(self, size=(100, 100), max_height=0.1, wave_length=0.3, center=(0., 0.), speed=3):
        self._size = size
        self._amplitude = max_height
        self._omega = 2 * np.pi / wave_length
        self._center = np.asarray(center, dtype=np.float32)
        self._speed = speed
        self.t = 0

    def height_and_normal(self):
        x = np.linspace(-1, 1, self._size[0])[:, None]
        y = np.linspace(-1, 1, self._size[1])[None, :]
        z = np.empty(self._size, dtype=np.float32)
        grad = np.zeros(self._size + (2,), dtype=np.float32)
        d = np.sqrt((x - self._center[0]) ** 2 + (y - self._center[1]) ** 2)
        arg = self._omega * d - self.t * self._speed
        z[:, :] = self._amplitude * np.cos(arg)
        dcos = -self._amplitude * self._omega * np.sin(arg)
        grad[:, :, 0] += (x - self._center[0]) * dcos / d
        grad[:, :, 1] += (y - self._center[1]) * dcos / d
        return z, grad


class ParallelWave(PlaneWaves):
    def __init__(self, size=(100, 100), g=1, max_height=0.0000001, speed=1, tau=0.004):
        self._size = size
        self._amplitude = max_height
        self._speed = speed
        x = np.linspace(-1, 1, self._size[0] + 1)[:, None]
        y = np.linspace(-1, 1, self._size[1])[None, :]
        h = np.zeros(self._size, dtype=np.float32)
        v = np.zeros(self._size, dtype=np.float32)
        for i in range(size[0]):
            value = max_height * np.sin(x[i] * np.pi)
            h[i] = value
            v[i] =  max_height * np.cos(x[i] * np.pi)
        self.p = np.array([h, v])
        self.tau = tau
        self.t = 0

    def f(self, p):
        n = self._size[0]
        h = p[0]
        ht = p[1]
        # hleft = np.roll(h, 1, axis=1)
        # hleft[:, 0] = 0
        # hright = np.roll(h, -1, axis=1)
        # hright[:, -1] = 0
        # htop = np.roll(h, 1, axis=0)
        # htop[0, :] = 0
        # hbot = np.roll(h, -1, axis=0)
        # hbot[-1, :] = 0
        hleft = np.roll(h, 1, axis=1)
        hright = np.roll(h, -1, axis=1)
        htop = np.roll(h, 1, axis=0)
        hbot = np.roll(h, -1, axis=0)
        vt = self._speed ** 2 / (2 / n) ** 2 * (hleft + hright + htop + hbot - 4 * h)
        return np.array([ht, vt])

    def height_and_normal(self):
        x = np.linspace(-1, 1, self._size[0])[:, None]
        y = np.linspace(-1, 1, self._size[1])[None, :]
        if self.t != self.tau:
            self.update_p()

        grad = np.zeros(self._size + (2,), dtype=np.float32)
        grad[:, :, 0] = self.p[1]
        grad[:, :, 1] = 0
        np_sum = np.sum(self.p[0])
        print(self.t, "{:e}".format(np_sum))
        return self.p[0], grad

    def update_p(self):
        k1 = self.f(self.p)
        k2 = self.f(self.p + self.tau / 2 * k1)
        k3 = self.f(self.p + self.tau / 2 * k2)
        k4 = self.f(self.p + self.tau * k3)
        self.p = self.p + self.tau / 6 * (k1 + 2 * k2 + 2 * k3 + k4)


class ParallelWaveEuler(ParallelWave):
    def __init__(self):
        ParallelWave.__init__(self)

    def update_p(self):
        temP = self.p + self.tau * self.f(self.p)
        newP = self.p + self.tau * (self.f(self.p) + self.f(temP)) / 2
        self.p = temP


class Surface(PlaneWaves):
    pass
